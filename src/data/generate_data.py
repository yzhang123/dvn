import numpy as np
import random
from os.path import join, dirname, abspath
import logging


from dvn.src.util.measures import oracle_score
from dvn.src.util.data import randomMask, blackMask, sampleExponential, zeroMask, oneMask
from dvn.src.util.data import left_upper1_4_mask, left_upper2_4_mask, left_upper3_4_mask, left_upper2_2_mask

from dvn.src.util.model import inference as infer, adversarial as adverse
from dvn.src.util.data import generate_random_sample




module_path = abspath(__file__)
dir_path = dirname(module_path)
root_path = join(dir_path, "../../")

class DataGenerator(object):

    def __init__(self, sess, net, data, train, data_update_rate):
        self.sess = sess
        self.graph = net
        self.data = data # (img, img_gt)
        self.data_update_rate = data_update_rate
        self.generators = [self.generate_examples(train=train)]

    def generate(self):
        while True:
            yield next(random.choice(self.generators))

    def gt(self):
        return self.data.__iter__()


    def generate_batch(self):
        """

        :return: images, input masks, and according ground truth masks as batches
        """
        shape = (self.data.height, self.data.width, self.data.num_classes)
        masks = list()
        masks.append(left_upper2_2_mask(shape))
        masks.append(left_upper1_4_mask(shape))
        masks.append(blackMask(shape))
        masks.append(left_upper2_4_mask(shape))
        masks.append(left_upper3_4_mask(shape))
        masks.append(zeroMask(shape))

        def _get_mask(img_mask):
            rand_idx = np.random.randint(0, len(masks) + 1)
            logging.info("mask %s" %rand_idx)
            if rand_idx < len(masks):
                return masks[rand_idx]
            else:
                return img_mask

        while(True):
            imgs, img_masks = next(self.gt())
            input_masks = list()
            for i in range(img_masks.shape[0]):
                mask = _get_mask(img_masks[i])
                input_masks.append(mask)

            input_masks = np.stack(input_masks, axis=0)

            assert imgs.shape > input_masks.shape, "imgs.shape : %s, input_masks.shape : %s" % (
            imgs.shape, input_masks.shape)
            assert img_masks.shape == input_masks.shape

            yield imgs, input_masks, img_masks


    def generate_examples(self, train=False):
        shape = (self.data.batch_size, self.data.size[0], self.data.size[1], self.data.num_classes)

        for img, img_gt in self.data:
            init_mask = self.get_initialization(shape)
            rand = np.random.rand()
            if train:
                if rand > 0.20:
                    logging.info("adverse")
                    gt_indices = np.random.rand(img_gt.shape[0]) > 0.3
                    init_mask[gt_indices] = img_gt[gt_indices].copy()
                    pred_mask = adverse(self.sess, self.graph, img, init_mask, img_gt, data_update_rate=self.data_update_rate, train=train, iterations=3)
                elif rand > 0.10:
                    logging.info("inference")
                    pred_mask = infer(self.sess, self.graph, img, init_mask, data_update_rate=self.data_update_rate, train=train, iterations=20)
                else:
                    # logging.info("rand")
                    # teta = 0.05
                    # pred_mask = generate_random_sample(shape, teta, img_gt)

                    logging.info("inference + gt")
                    pred_mask = infer(self.sess, self.graph, img, init_mask, data_update_rate=self.data_update_rate, train=train, iterations=20)
                    number_elements = len(np.reshape(pred_mask, -1))
                    rand_positions = np.random.choice(number_elements, int(0.5 * number_elements))
                    for pos in rand_positions:
                        idx3 = pos % self.data.num_classes
                        pos  = pos // self.data.num_classes
                        idx2 = pos % self.data.size[1]
                        pos  = pos // self.data.size[1]
                        idx1 = pos % self.data.size[0]
                        pos  = pos // self.data.size[0]
                        idx0 = pos % self.data.batch_size
                        pred_mask[idx0][idx1][idx2][idx3] = img_gt[idx0][idx1][idx2][idx3]
            else:
                pred_mask = infer(self.sess, self.graph, img, init_mask, data_update_rate=self.data_update_rate, train=train, iterations=20)
            yield img, pred_mask, img_gt
            # yield img, init_mask, img_gt

    def get_initialization(self, shape):
        black_batch = zeroMask(shape)
        return black_batch


if __name__=='__main__':
    img_path = join(dir_path, "../../", "data/weizmann_horse_db/rgb_1")
    test_img_path = join(dir_path, "../../", "data/weizmann_horse_db/gray_1")
    img_gt_path = join(dir_path, "../../", "data/weizmann_horse_db/figure_ground_1")
    print("img_dir %s" % img_path)
    print("img_gt_dir %s" % img_gt_path)

    classes = ['__background__', 'horse']
    from dvn.src.model.dvn import DvnNet
    from dvn.src.data.data_set import DataSet
    import tensorflow as tf
    from dvn.src.util.measures import _oracle_score_cpu

    data = DataSet(classes, img_path, img_gt_path, batch_size=1)
    generator = DataGenerator(sess=None, net=None, data=data, train=False, data_update_rate=0)
    for img, mask, img_gt in generator.helper():
        print("mask shape ")
        print( mask.shape)
        print("y_mean")
        print(np.mean(mask, (1,2))[..., 1])
        print("oracle score ")
        print(_oracle_score_cpu(mask, img_gt))
        print("\n")