import chainer
import chainer.functions as F
import chainer.links as L
import numpy as np
import csv

class Net(chainer.Chain):
	def __init__(self, n_history=3, n_action=3):
		initializer = chainer.initializers.HeNormal()
		super(Net, self).__init__(
			conv1=L.Convolution2D(n_history, 32, ksize=8, stride=4, nobias=False, initialW=initializer),
			conv2=L.Convolution2D(32, 64, ksize=3, stride=2, nobias=False, initialW=initializer),
			conv3=L.Convolution2D(64, 64, ksize=3, stride=1, nobias=False, initialW=initializer),
			fc4=L.Linear(960, 512, initialW=initializer),
			fc5=L.Linear(512, 256, initialW=initializer),
			lstm6 = L.LSTM(256,256),
			fc7=L.Linear(256,128),
			fc8=L.Linear(128, n_action, initialW=np.zeros((n_action, 128), dtype=np.float32))
		)

	def reset_state(self):
        self.lstm.reset_state()

	def __call__(self, x, test=False):
		s = chainer.Variable(x)
		h1 = F.relu(self.conv1(s))
		h2 = F.relu(self.conv2(h1))
		h3 = F.relu(self.conv3(h2))
		h4 = F.relu(self.fc4(h3))
		h5 = F.relu(self.fc5(h4))
		h6 = F.relu(self.lstm6(h5))
		h7 = F.relu(self.fc7(h6))
		h  = self.fc8(h7)
		return h

class cloning_learning:
	def __init__(self, n_channel=3, n_action=1, seq_len=10, support_len=10, repeat=True, pred=1)):
		self.seq_length = seq_len
        self.support_len = support_len
		self.pred = pred
        self.batch_size = batch_size
        self.repeat = repeat
		self.net = Net(n_channel, n_action)
		self.optimizer = chainer.optimizers.Adam(eps=1e-2)
		self.optimizer.setup(self.net)
		self.optimizer.add_hook(chainer.optimizer.WeightDecay(5e-4))
		self.n_action = n_action
		self.phi = lambda x: x.astype(np.float32, copy=False)
		self.count = 0
		self.accuracy = 0
		self.results_train = {}
		self.results_train['loss'], self.results_train['accuracy'] = [], []
		self.loss_list = []
		self.acc_list = []
		self.data = []
		self.target_angles = []

	def act_and_trains(self, imgobj, target_angle):		
		x = [self.phi(s) for s in [imgobj]]
		t = np.array([target_angle], np.float32)
		self.data.append(x[0])
		self.target_angles.append(t[0])
		if len(self.data) > MAX_DATA:
			del self.data[0]
			del self.target_angles[0]
		dataset = TupleDataset(self.data, self.target_angles)
		train_iter = SerialIterator(dataset, batch_size = BATCH_SIZE, repeat=True, shuffle=True)
		train_batch  = train_iter.next()
		x_train, t_train = chainer.dataset.concat_examples(train_batch, -1)

		y_train = self.net(x_train)
		loss_train = F.mean_squared_error(y_train, Variable(t_train.reshape(BATCH_SIZE, 1)))

		self.loss_list.append(loss_train.array)

		self.net.cleargrads()
		loss_train.backward()
		self.optimizer.update()
			
		self.count += 1

		self.results_train['loss'] .append(loss_train.array)
		x_test = chainer.dataset.concat_examples(x, -1)
		with chainer.using_config('train', False), chainer.using_config('enable_backprop', False):
			action_value = self.net(x_test)
		return action_value.data[0][0], loss_train.array

	def act(self, imgobj):
		x = [self.phi(s) for s in [imgobj]]
		x_test = chainer.dataset.concat_examples(x, -1)

		with chainer.using_config('train', False), chainer.using_config('enable_backprop', False):
			action_value = self.net(x_test)
		return action_value.data[0][0]

	def result(self):
		accuracy = self.accuracy
		return accuracy

    def save(self, save_path):
        path = save_path + time.strftime("%Y%m%d_%H:%M:%S")

    def load(self, load_path):
        chainer.serializers.load_npz(load_path , self.net)

if __name__ == '__main__':
        cl = cloning_learning()