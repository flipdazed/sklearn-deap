import os
import tempfile
import numpy as np
import pandas as pd
import cPickle as pkl

# plotting junk
import matplotlib.pyplot as plt
from matplotlib import gridspec
from matplotlib.colors import ListedColormap
from mpl_toolkits.axes_grid.anchored_artists import AnchoredText

# preprocessing / validation utils
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.model_selection import StratifiedShuffleSplit
from sklearn.datasets import make_moons, make_circles, make_classification

# the classifiers
from sklearn.neural_network import MLPClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import SVC
from sklearn.gaussian_process import GaussianProcessClassifier
from sklearn.gaussian_process.kernels import RBF, DotProduct
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier, AdaBoostClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.discriminant_analysis import QuadraticDiscriminantAnalysis

# this is my modified DEAP code - make sure you use my fork
# as the master branch is buggy!
from evolutionary_search import EvolutionaryAlgorithmSearchCV


names = ["KNN", "Gaussian Proc.", "Dec. Tree", "Rand. Forest",
        "RBF SVM", "Linear SVM", "Neural Net", "AdaBoost", "QDA"]

classifiers = [
    [KNeighborsClassifier,      {'n_neighbors': range(1, 10), 'weights': ['uniform', 'distance']}],
    [DecisionTreeClassifier,    {'max_depth': range(1, 20), "splitter": ['best', 'random'],
                                 'min_samples_split': range(1, 20), 'min_samples_leaf': range(1, 20),
                                 'random_state': [42], 'criterion': ['gini', 'entropy']}
    ],
    [RandomForestClassifier,    {'max_depth': range(1, 20), 'n_estimators': range(1, 20),
                                 'min_samples_split': range(1, 20), 'min_samples_leaf': range(1, 20),
                                 'random_state': [42], 'criterion': ['gini', 'entropy']}
    ],
    [MLPClassifier,             {'hidden_layer_sizes': range(5, 200, 5) +
                                     list(itertools.permutations(range(5, 200, 5), 2)),
                                 'activation': ['logistic', 'tanh', 'relu'],
                                 'solver': ['sgd', 'adam'], 'batch_size': range(1, 50),
                                 'random_state': [42],
                                 'alpha':np.logspace(-9, 9, num=100, base=2),
                                 'learning_rate': ['constant', 'invscaling', 'adaptive']}
    ],
    [SVC,                       {'kernel':['rbf'], 'gamma': np.logspace(-9, 9, num=1000, base=2),
                                 'C': np.logspace(-9, 9, num=1000, base=2)}
    ],
    [SVC,                       {'kernel':["linear"], 'C': np.logspace(-9, 9, num=1000, base=2)}],
    [GaussianProcessClassifier, {'max_iter_predict': range(50, 200, 10),
                                 'kernel': [1.0 * RBF(1.0), 1.0 * DotProduct(sigma_0=1.0)**2]}],
    [AdaBoostClassifier,        {'n_estimators': range(10, 100, 2),
                                 'learning_rate': np.logspace(-9, 9, num=1000, base=2),
                                 'algorithm': ['SAMME', 'SAMME.R']}],
    [QuadraticDiscriminantAnalysis, {'reg_param': np.logspace(-9, 9, num=1000, base=2)}],
]

generic_args = {'scoring': "accuracy",
                # cross validation method
                'cv': StratifiedShuffleSplit(n_splits=5, test_size=0.5, random_state=42),
                'verbose': 1,
                # genetic algorithm params are quite straightforward to pick though
                # if the output looks rubbish do some googling and tweak
                'population_size': 200,
                'gene_mutation_prob': 0.08,
                'gene_crossover_prob': 0.5,
                'tournament_size': 3,
                'generations_number': 50,
                'n_jobs': 6}  # parallel processes

X, y = make_classification(n_features=2, n_redundant=0, n_informative=2,
                           random_state=1, n_clusters_per_class=1)
rng = np.random.RandomState(2)
X += 2 * rng.uniform(size=X.shape)
linearly_separable = (X, y)

datasets = [make_moons(noise=0.3, random_state=0),
            make_circles(noise=0.2, factor=0.5, random_state=1),
            linearly_separable]


def plot_from_data(plot_data_location):
    """Returns the ``fig, axes`` for a ``plot_data.pkl`` generated by this script.
    Axes is a dictionary of format {''}
    """
    with open(plot_data_location, 'r') as f:
        plot_data = pkl.load(f)

    fig = plt.figure()
    plt_grid = gridspec.GridSpec(len(datasets)*2, len(classifiers)+1, wspace=0, hspace=0)

    cm = plt.cm.RdBu
    cm_bright = ListedColormap(['#FF0000', '#0000FF'])

    plt.ion()
    axes = {}
    # iterate over datasets
    for ds_cnt, ds in enumerate(datasets):
        ax = fig.add_subplot(plt_grid[ds_cnt*2:(ds_cnt+1)*2, 0])
        X_train = plot_data[ds_cnt]['scat1']['X_train']
        X_test =  plot_data[ds_cnt]['scat1']['X_test']
        y_test =  plot_data[ds_cnt]['scat1']['y_test']
        y_train = plot_data[ds_cnt]['scat1']['y_train']
        xx = plot_data[ds_cnt]['scat1']['xx']
        yy = plot_data[ds_cnt]['scat1']['yy']

        ax.scatter(X_train[:, 0], X_train[:, 1], c=y_train, cmap=cm_bright, marker='x', alpha=0.6,
                   edgecolors='k', label='train')
        ax.scatter(X_test[:, 0], X_test[:, 1], c=y_test, cmap=cm_bright, edgecolors='k', label='test')
        if ds_cnt == len(datasets) - 1:
            ax.legend(fontsize=8, loc=2)
        ax.set_xlim(xx.min(), xx.max())
        ax.set_ylim(yy.min(), yy.max())
        ax.set_xticks(())
        ax.set_yticks(())
        axes[ds_cnt] = {'input_data':ax}

        plt.draw()
        plt.pause(0.05)


        for i, (name, (_, params)) in enumerate(zip(names, classifiers), 1):
            ax = fig.add_subplot(plt_grid[ds_cnt*2:ds_cnt*2+1, i])

            Z = plot_data[ds_cnt][name]['Z']
            Z = Z.reshape(xx.shape)
            score = plot_data[ds_cnt][name]['v_score']
            t_score = plot_data[ds_cnt][name]['t_score']
            all_logbooks = plot_data[ds_cnt][name]['all_logbooks']

            ax.contourf(xx, yy, Z, cmap=cm, alpha=.8)
            ax.scatter(X_train[:, 0], X_train[:, 1], c=y_train, cmap=cm_bright,
                       marker='x', edgecolors='k', s=15, alpha=0.6)
            ax.scatter(X_test[:, 0], X_test[:, 1], c=y_test, cmap=cm_bright, edgecolors='k', s=15)

            ax.set_xlim(xx.min(), xx.max())
            ax.set_ylim(yy.min(), yy.max())
            ax.set_xticks(())
            ax.set_yticks(())
            if ds_cnt == 0:
                ax.set_title(name, fontsize=8)
            axes[ds_cnt][name]['clf'] = ax

            ax = fig.add_subplot(plt_grid[ds_cnt*2+1:(ds_cnt+1)*2, i])
            pd.DataFrame(all_logbooks).set_index('gen')[['max', 'avg']].plot(ax=ax, fig=fig, legend=ds_cnt==len(datasets))
            ax.set_ylim(0., 1.)

            if (i != len(classifiers)) or (ds_cnt != len(datasets) - 1):
                ax.set_yticks(())
                ax.set_xticks(())
                ax.xaxis.label.set_visible(False)
                ax.add_artist(AnchoredText('{}|{}'.format(('%.2f' % t_score).lstrip('0'),
                                                   ('%.2f' % score).lstrip('0')),
                                           loc=4, prop={'size':10}))
            else:
                ax.yaxis.tick_right()
                ax.add_artist(AnchoredText('Valid|Test\n{}|{}'.format(('%.2f' % t_score).lstrip('0'),
                                                   ('%.2f' % score).lstrip('0')),
                                           loc=4, prop={'size':10}))

            axes[ds_cnt][name]['ga'] = ax
            plt.draw()
            plt.pause(0.05)
        fig.subplots_adjust(left=0.02, right=0.96, top=0.96, bottom=0.06)
        plt.show()
    return fig, axes


if __name__ == '__main__':

    plot_data = {}

    fig = plt.figure()
    plt_grid = gridspec.GridSpec(len(datasets)*2, len(classifiers)+1, wspace=0, hspace=0)

    plt.ion()
    # iterate over datasets
    for ds_cnt, ds in enumerate(datasets):
        plot_data[ds_cnt] = {}
        # preprocess dataset, split into training and test part
        X, y = ds
        X = StandardScaler().fit_transform(X)
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=.25, random_state=42)
        h = .02  # step size in the mesh
        x_min, x_max = min([X[:, 0].min(), X[:, 0].min()]) - .5, max([X[:, 0].max(), X[:, 0].max()]) + .5
        y_min, y_max = min([X[:, 1].min(), X[:, 1].min()]) - .5, max([X[:, 1].max(), X[:, 1].max()]) + .5
        xx, yy = np.meshgrid(np.arange(x_min, x_max, h), np.arange(y_min, y_max, h))

        # just plot the dataset first
        cm = plt.cm.RdBu
        cm_bright = ListedColormap(['#FF0000', '#0000FF'])
        ax = fig.add_subplot(plt_grid[ds_cnt*2:(ds_cnt+1)*2, 0])
        if ds_cnt == 0:
            ax.set_title("Input data", fontsize=8)
        # Plot the training points
        plot_data[ds_cnt]['scat1'] = {'X_train': X_train, 'y_train': y_train, 'X_test': X_test, 'y_test': y_test, 'xx': xx, 'yy': yy}
        ax.scatter(X_train[:, 0], X_train[:, 1], c=y_train, cmap=cm_bright, marker='x', alpha=0.6,
                   edgecolors='k', label='train')
        # and testing points
        ax.scatter(X_test[:, 0], X_test[:, 1], c=y_test, cmap=cm_bright, edgecolors='k', label='test')
        if ds_cnt == len(datasets) - 1:
            ax.legend(fontsize=8, loc=2)
        ax.set_xlim(xx.min(), xx.max())
        ax.set_ylim(yy.min(), yy.max())
        ax.set_xticks(())
        ax.set_yticks(())
        plt.draw()
        plt.pause(0.05)

        # iterate over classifiers
        for i, (name, (clf, params)) in enumerate(zip(names, classifiers), 1):
            plot_data[ds_cnt]['scat1'][name] = {}

            ax = fig.add_subplot(plt_grid[ds_cnt*2:ds_cnt*2+1, i])
            try:
                clf =  EvolutionaryAlgorithmSearchCV(estimator=clf(), params=params,
                                                     **generic_args).fit(X_train, y_train)
            except:
                print 'failed to do: {}'.format(name)
                continue
            score = clf.score(X_test, y_test)

            # Plot the decision boundary. For that, we will assign a color to each
            # point in the mesh [x_min, x_max]x[y_min, y_max].
            if hasattr(clf, "decision_function"):
                Z = clf.decision_function(np.c_[xx.ravel(), yy.ravel()])
            else:
                Z = clf.predict_proba(np.c_[xx.ravel(), yy.ravel()])[:, 1]

            # Put the result into a color plot
            Z = Z.reshape(xx.shape)
            plot_data[ds_cnt][name] = {'Z': Z, 'v_score': score, 't_score': clf.best_score_, 'all_logbooks': clf.all_logbooks_[0]}
            ax.contourf(xx, yy, Z, cmap=cm, alpha=.8)

            # Plot also the training points
            ax.scatter(X_train[:, 0], X_train[:, 1], c=y_train, cmap=cm_bright,
                       marker='x', edgecolors='k', s=15, alpha=0.6)
            # and testing points
            ax.scatter(X_test[:, 0], X_test[:, 1], c=y_test, cmap=cm_bright, edgecolors='k', s=15)

            ax.set_xlim(xx.min(), xx.max())
            ax.set_ylim(yy.min(), yy.max())
            ax.set_xticks(())
            ax.set_yticks(())
            if ds_cnt == 0:
                ax.set_title(name, fontsize=8)

            # ax.annotate(xx.max() - .3, yy.min() - .1*yy.max(), ('%.2f' % score).lstrip('0'),
            #         size=11, horizontalalignment='right', verticalalignment='bottom')

            ax = fig.add_subplot(plt_grid[ds_cnt*2+1:(ds_cnt+1)*2, i])
            pd.DataFrame(clf.all_logbooks_[0]).set_index('gen')[['max', 'avg']].plot(ax=ax, fig=fig, legend=ds_cnt==len(datasets))
            ax.set_ylim(0., 1.)

            if (i != len(classifiers)) or (ds_cnt != len(datasets) - 1):
                ax.set_yticks(())
                ax.set_xticks(())
                ax.xaxis.label.set_visible(False)
                ax.add_artist(AnchoredText('{}|{}'.format(('%.2f' % clf.best_score_).lstrip('0'),
                                                   ('%.2f' % score).lstrip('0')),
                                           loc=4, prop={'size':10}))
            else:
                ax.yaxis.tick_right()
                ax.add_artist(AnchoredText('Valid|Test\n{}|{}'.format(('%.2f' % clf.best_score_).lstrip('0'),
                                                   ('%.2f' % score).lstrip('0')),
                                           loc=4, prop={'size':10}))

            plt.draw()
            plt.pause(0.05)
            del clf
        fig.subplots_adjust(left=0.02, right=0.96, top=0.96, bottom=0.06)

    # with open(os.path.join(tempfile.gettempdir(), 'all_classifiers.pkl'), 'w') as f:
    #     pkl.dump(plot_data, f)