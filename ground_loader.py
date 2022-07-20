# ====================================================
# @Author  : Xiao Junbin
# @Email   : junbin@comp.nus.edu.sg
# @File    : ground_loader.py
# ====================================================
import torch
from torch.utils.data import Dataset, DataLoader
from torch.utils.data import DataLoader, RandomSampler, DistributedSampler, SequentialSampler
from .util import load_file, pkdump, pkload
import os.path as osp
import numpy as np
import nltk
import pickle as pkl

class RelationDataset(Dataset):
    """load the dataset in dataloader"""

    def __init__(self, video_feature_path, video_feature_cache, sample_list_path, vocab, mode, nframes, nbbox, visual_dim):
        self.video_feature_path = video_feature_path
        self.vocab = vocab
        self.frame_steps = nframes
        self.nbbox = nbbox
        sample_list_file = osp.join(sample_list_path, 'vrelation_{}.json'.format(mode))
        # sample_list_file = '/opt/data/private/transformer/vRGV-master/dataset/vidvrd/static_val.txt'
        # sample_list_file = '/opt/data/private/transformer/vRGV-master/dataset/vidvrd/vrelation_zero.json'
        self.sample_list = load_file(sample_list_file)
        self.feat_dim = visual_dim
        self.video_feature_cache = video_feature_cache


    def __len__(self):
        return len(self.sample_list)

    def select_bbox(self, roi_bbox, roi_classme, width, height):
        """
        select the bboxes with maximun confidence
        :param roi_bbox:
        :param roi_classme:
        :return:
        """
        bbox, classme = roi_bbox.squeeze(), roi_classme.squeeze()
        classme = classme[:, 1:]  # skip background
        index = np.argmax(classme, 1)
        bbox = np.asarray([bbox[i][4 * (index[i] + 1):4 * (index[i] + 1) + 4] for i in range(len(bbox))])
        relative_bbox = bbox / np.asarray([width, height, width, height])
        area = (bbox[:,2]-bbox[:,0]+1)*(bbox[:,3]-bbox[:,1]+1)
        relative_area = area/(width*height)
        relative_area = relative_area.reshape(-1, 1)
        relative_bbox = np.hstack((relative_bbox, relative_area))

        return relative_bbox


    def get_video_feature(self, video_name, frame_count, width, height):
        """
        :param video_name:
        :param frame_count:
        :param width:
        :param height:
        :return:
        """
        video_feature_folder = osp.join(self.video_feature_path, video_name)
        cache_file = osp.join(self.video_feature_cache, '{}.pkl'.format(video_name))
        if osp.exists(cache_file) and osp.getsize(cache_file) > 0:
            video_feature = pkload(cache_file)
            return video_feature
        sample_frames = np.round(np.linspace(0, frame_count - 1, self.frame_steps))
        video_feature = torch.zeros(len(sample_frames), self.nbbox, self.feat_dim)
        for i, fid in enumerate(sample_frames):
            frame_name = osp.join(video_feature_folder, str(int(fid)).zfill(6)+'.pkl')
            with open(frame_name, 'rb') as fp:
                feat = pkl.load(fp)
            roi_feat = feat['roi_feat'] #40x2048
            roi_bbox = feat['bbox']
            roi_classme = feat['cls_prob'] #40 x 81
            bbox = self.select_bbox(roi_bbox, roi_classme, width, height) # 40 x 5
            cb_feat = np.hstack((roi_feat, bbox))

            video_feature[i] = torch.Tensor(cb_feat)

        pkdump(video_feature, cache_file)

        return video_feature


    def get_word_idx(self, relation):
        """
        convert relation to index sequence
        :param relation:
        :return:
        """
        # relation = relation.split('-')
        # relation = '-'.join([relation[0],relation[-1]])

        table = str.maketrans('-_', '  ')
        relation_trans = relation.translate(table)

        tokens = nltk.tokenize.word_tokenize(str(relation_trans).lower())
        relation_token = []
        relation_token.append(self.vocab('<start>'))
        relation_token.extend([self.vocab(token) for token in tokens])
        relation_token.append(self.vocab('<end>'))
        target = torch.Tensor(relation_token)

        return target


    def __getitem__(self, idx):
        """
        return an item from data list as tuple (video, relation)
        :param idx:
        :return:
                -video: torch tensor (nframe, nbbox, feat)
                -relation: torch tensor of variable length
        """
        video_name, frame_count, width, height, relation = self.sample_list[idx]
        video_feature = self.get_video_feature(video_name, frame_count, width, height)

        relation2idx = self.get_word_idx(relation)
        return video_feature, relation2idx, relation, video_name


class RelationLoader():
    def __init__(self, batch_size, num_worker, video_feature_path, video_feature_cache,
                 sample_list_path, vocab, nframes, nbbox, visual_dim, train_shuffle=True, val_shuffle=False):
        self.batch_size = batch_size
        self.num_worker = 1
        self.video_feature_path = video_feature_path
        self.video_feature_cache = video_feature_cache
        self.sample_list_path = sample_list_path
        self.vocab = vocab
        self.nframes = nframes
        self.nbbox = nbbox
        self.visual_dim = visual_dim
        self.train_shuffle = train_shuffle
        self.val_shuffle = val_shuffle


    def run(self, mode='',args=None):

        if mode == 'val':
            train_loader = ''
        else:
            train_loader = self.train(args)
        val_loader = self.validate(args)
        return train_loader, val_loader

    def train(self,args):

        # print("Now in train")
        # applying transformation on training videos
        training_set = RelationDataset(self.video_feature_path, self.video_feature_cache, self.sample_list_path,
                                       self.vocab, 'train', self.nframes, self.nbbox,
                                       self.visual_dim)

        train_sampler = RandomSampler(training_set) if args.local_rank == -1 else DistributedSampler(training_set)

        # if args.local_rank == -1:
        #     sampler_train = DistributedSampler(training_set)
        #
        # else:
        #     sampler_train = torch.utils.data.RandomSampler(training_set)
        #
        #
        # batch_sampler_train = torch.utils.data.BatchSampler(
        #     sampler_train, args.batch_size, drop_last=True)
        #
        # train_loader = DataLoader(training_set, batch_sampler=batch_sampler_train,
        #                                collate_fn=collate_fn, num_workers=args.num_workers)

        print('Eligible video-relation pairs for training : {}'.format(len(training_set)))
        train_loader = DataLoader(
            training_set,
            sampler=train_sampler,
            batch_size=self.batch_size,
            # shuffle=self.train_shuffle,
            num_workers=2,
            pin_memory=True,
            drop_last=True,
            collate_fn=collate_fn)

        return train_loader

    def validate(self,args):
        # if args.local_rank == 0:
        #     torch.distributed.barrier()
        # print("Now in Validate")
        # applying transformation for validation videos
        validation_set = RelationDataset(self.video_feature_path, self.video_feature_cache, self.sample_list_path,
                                         self.vocab, 'val', self.nframes, self.nbbox,
                                         self.visual_dim)

        # if args.local_rank == -1:
        #     sampler_val = DistributedSampler(validation_set, shuffle=False)
        # else:
        #     sampler_val = torch.utils.data.SequentialSampler(validation_set)
        #
        # val_loader = DataLoader(validation_set, args.batch_size, sampler=sampler_val,
        #                              drop_last=True, collate_fn=collate_fn, num_workers=args.num_workers)


        test_sampler = torch.utils.data.SequentialSampler(validation_set) #if args.local_rank == -1 else DistributedSampler(validation_set)

        print('Eligible video-relation pairs for validation : {}'.format(len(validation_set)))
        val_loader = DataLoader(
            validation_set,
            sampler=test_sampler,
            batch_size=self.batch_size,
            shuffle=self.val_shuffle,
            num_workers=2,
            pin_memory=True,
            drop_last=False,
            collate_fn=collate_fn)

        return val_loader


def collate_fn (data):
    """
    Create mini-batch tensors from the list of tuples (video, relation)
    :param data:
                -video: torch tensor of shape (nframe, nbbox, feat_dim)
                -relation2idx: torch tensor of variable length
                -relation: raw relation
                -video_name: str
    :return:
        images: torch tensor of shape (batch_size, nframe, nbbox, feat_dim)
        targets: torch tensor of shape (batch_size, padded_length)
        length: valid length for each padded length
    """
    data.sort(key=lambda x : len(x[1]), reverse=True)
    videos, relation2idx, relations, video_name = zip(*data)

    #merge videos
    videos = torch.stack(videos, 0)

    #merge relations
    lengths = [len(rel) for rel in relation2idx]
    targets = torch.zeros(len(relation2idx), max(lengths)).long()
    for i, rel in enumerate(relation2idx):
        end = lengths[i]
        targets[i, :end] = rel[:end]

    return relations, videos, targets, lengths, video_name
