from torch.utils.data import Sampler
from typing import List, Iterable, Callable, Tuple
import numpy as np
import torch

from few_shot.metrics import categorical_accuracy
from few_shot.callbacks import Callback


class NShotTaskSampler(Sampler):
    def __init__(self,
                 dataset: torch.utils.data.Dataset,
                 episodes_per_epoch: int = None,
                 n: int = None,
                 k: int = None,
                 q: int = None,
                 num_tasks: int = 1,
                 fixed_tasks: List[Iterable[int]] = None):
        """PyTorch Sampler subclass that generates batches of n-shot, k-way, q-query tasks.

        Each n-shot task contains a "support set" of `k` sets of `n` samples and a "query set" of `k` sets
        of `q` samples. The support set and the query set are all grouped into one Tensor such that the first n * k
        samples are from the support set while the remaining q * k samples are from the query set.

        The support and query sets are sampled such that they are disjoint i.e. do not contain overlapping samples.

        # Arguments
            dataset: Instance of torch.utils.data.Dataset from which to draw samples
            episodes_per_epoch: Arbitrary number of batches of n-shot tasks to generate in one epoch
            n_shot: int. Number of samples for each class in the n-shot classification tasks.
            k_way: int. Number of classes in the n-shot classification tasks.
            q_queries: int. Number query samples for each class in the n-shot classification tasks.
            num_tasks: Number of n-shot tasks to group into a single batch
            fixed_tasks: If this argument is specified this Sampler will always generate tasks from
                the specified classes
        """
        super(NShotTaskSampler, self).__init__(dataset)
        self.episodes_per_epoch = episodes_per_epoch
        self.dataset = dataset
        if num_tasks < 1:
            raise ValueError('num_tasks must be > 1.')

        self.num_tasks = num_tasks
        # TODO: Raise errors if initialise badly
        ### k is unused!
        #self.k = k
        self.n = n
        self.q = q
        self.fixed_tasks = fixed_tasks

        self.i_task = 0

    def __len__(self):
        return self.episodes_per_epoch

    def __iter__(self):
        ### How many batches per epoch?
        for _ in range(self.episodes_per_epoch):
            #print(self.episodes_per_epoch)

            ###a batch consists of num_tasks nshot tasks
            batch = []
            #print(self.n)
            #print(self.k)
            #print(self.q)

            ### selct boards for tasks in this meta batch
            if self.dataset.subset is 'background':
                task_boards = np.random.choice(self.dataset.df['board_id'].unique(), size=self.num_tasks, replace=False)

                for board_id in task_boards:

                    #if self.fixed_tasks is None:
                    # Get random classes
                    '''
                    episode_boards = np.random.choice(self.dataset.df['board_id'].unique(), size=self.k, replace=False)
                #else:
                    # Loop through classes in fixed_tasks
                #    episode_classes = self.fixed_tasks[self.i_task % len(self.fixed_tasks)]
                #    self.i_task += 1
                #print(episode_boards)
                    df = self.dataset.df[self.dataset.df['board_id'].isin(episode_boards)]

                #print(task)
                #print(episode_boards)


                    support_k = {k: None for k in episode_boards}
                    #print(len(support_k))
                    for k in episode_boards:
                    # Select support examples
                        support = df[df['board_id'] == k].sample(self.n)
                        support_k[k] = support

                    #print(support)

                        for i, s in support.iterrows():
                            batch.append(s['id'])

                    for k in episode_boards:
                        query = df[(df['board_id'] == k) & (~df['id'].isin(support_k[k]['id']))].sample(self.q)
                        for i, q in query.iterrows():
                            batch.append(q['id'])
                    '''


                    ### get all smaples from current board

                    #samples of board with id board_id
                    df = self.dataset.df[self.dataset.df['board_id']==board_id]

                    assert self.n+self.q <= df.shape[0]

                    support = df.sample(self.n+self.q)
                    #print(support)
                    query = support.sample(self.q)
                    #print(query.index)
                    support = support.drop(query.index)

                    assert support.shape[0] == self.n and query.shape[0] == self.q

                    for _, s in support.iterrows():
                        batch.append(s['id'])
                    for _, q in query.iterrows():
                        batch.append(q['id'])

            else:
                df = self.dataset.df # there is just one board in the eval dataset

                #print(df.shape)
                assert self.n+self.q <= df.shape[0]

                support = df.sample(self.n+self.q)
                query = support.sample(self.q)
                support = support.drop(query.index)

                assert support.shape[0] == self.n and query.shape[0] == self.q

                for _, s in support.iterrows():
                    batch.append(s['id'])
                for _, q in query.iterrows():
                    batch.append(q['id'])

            #print((batch.dtype))
            #print((np.stack(batch).dtype))
            #print(self.dataset.subset)
            #print(np.stack(batch))
            yield np.stack(batch)


class EvaluateFewShot(Callback):
    """Evaluate a network on  an n-shot, k-way classification tasks after every epoch.

    # Arguments
        eval_fn: Callable to perform few-shot classification. Examples include `proto_net_episode`,
            `matching_net_episode` and `meta_gradient_step` (MAML).
        num_tasks: int. Number of n-shot classification tasks to evaluate the model with.
        n_shot: int. Number of samples for each class in the n-shot classification tasks.
        k_way: int. Number of classes in the n-shot classification tasks.
        q_queries: int. Number query samples for each class in the n-shot classification tasks.
        task_loader: Instance of NShotWrapper class
        prepare_batch: function. The preprocessing function to apply to samples from the dataset.
        prefix: str. Prefix to identify dataset.
    """

    def __init__(self,
                 eval_fn: Callable,
                 num_tasks: int,
                 n_shot: int,
                 k_way: int,
                 q_queries: int,
                 taskloader: torch.utils.data.DataLoader,
                 prepare_batch: Callable,
                 prefix: str = 'val_',
                 **kwargs):
        super(EvaluateFewShot, self).__init__()
        self.eval_fn = eval_fn
        self.num_tasks = num_tasks
        self.n_shot = n_shot
        self.k_way = k_way
        self.q_queries = q_queries
        self.taskloader = taskloader
        self.prepare_batch = prepare_batch
        self.prefix = prefix
        self.kwargs = kwargs
        self.metric_name = f'{self.prefix}{self.n_shot}-shot_{self.k_way}-way_acc'

    def on_train_begin(self, logs=None):
        self.loss_fn = self.params['loss_fn']
        self.optimiser = self.params['optimiser']

    def on_epoch_end(self, epoch, logs=None):
        logs = logs or {}
        seen = 0
        totals = {'loss': 0, self.metric_name: 0}
        for batch_index, batch in enumerate(self.taskloader):
            x, y = self.prepare_batch(batch)

            loss, y_pred = self.eval_fn(
                self.model,
                self.optimiser,
                self.loss_fn,
                x,
                y,
                n_shot=self.n_shot,
                k_way=self.k_way,
                q_queries=self.q_queries,
                train=False,
                **self.kwargs
            )

            seen += y_pred.shape[0]

            totals['loss'] += loss.item() * y_pred.shape[0]
            totals[self.metric_name] += categorical_accuracy(y[:,-1:,:], y_pred)# * y_pred.shape[0]

        logs[self.prefix + 'loss'] = totals['loss'] / seen
        logs[self.metric_name] = totals[self.metric_name] / seen


def prepare_nshot_taska(n: int, k: int, q: int) -> Callable:
    """Typical n-shot task preprocessing.

    # Arguments
        n: Number of samples for each class in the n-shot classification task
        k: Number of classes in the n-shot classification task
        q: Number of query samples for each class in the n-shot classification task

    # Returns
        prepare_nshot_task_: A Callable that processes a few shot tasks with specified n, k and q
    """
    def prepare_nshot_task_(batch: Tuple[torch.Tensor, torch.Tensor]) -> Tuple[torch.Tensor, torch.Tensor]:
        """Create 0-k label and move to GPU.

        TODO: Move to arbitrary device
        """
        x, y = batch
        x = x.double().cuda()
        # Create dummy 0-(num_classes - 1) label
        y = create_nshot_task_label(k, q).cuda()
        return x, y

    return prepare_nshot_task_


def create_nshot_task_label(k: int, q: int) -> torch.Tensor:
    """Creates an n-shot task label.

    Label has the structure:
        [0]*q + [1]*q + ... + [k-1]*q

    # TODO: Test this

    # Arguments
        k: Number of classes in the n-shot classification task
        q: Number of query samples for each class in the n-shot classification task

    # Returns
        y: Label vector for n-shot task of shape [q * k, ]
    """
    y = torch.arange(0, k, 1 / q).long()
    return y
