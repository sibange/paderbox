"""Sacred helper when used for local folders with JsonObserver.

Support for MongoDB has been dropped. If you still need it, let us know.
"""
from pathlib import Path
import datetime

from sacred import Experiment
from sacred.observers import JsonObserver


class LocalExperiment(Experiment):
    """Experiment with automatically added JsonObserver."""
    def __init__(self, data_root: Path, experiment_name: str):
        """Simplifies experiment creation. Automatically adds date prefix.

        Assumes, that you have a data root which may contain more than one
        exeperiment.

        Args:
            data_root: Path object, i.e. Path('/net/vol/project/data')
            experiment_name: String, i.e. 'enhancement'
        Returns:
            Experiment to be used as decorator in main Sacred file.
        """
        super(LocalExperiment, self).__init__(experiment_name)
        self.observers.append(JsonObserver.create(
            data_root / experiment_name,
            prefix=datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S_')
        ))

    @property
    def target_path(self):
        """Short name to get target folder (use in main function)."""
        return self.observers[0].folder


def get_path_by_id(
    data_root: Path,
    experiment_name: str,
    _id: str
):
    """Helps to get full path, if you just know the previous ID.

    Args:
        data_root: Path object, i.e. Path('/net/vol/project/data')
        experiment_name: String, i.e. 'enhancement'
        _id: Desired ID as string, i.e. '58e23bbf6753904febf824eb'
    """
    experiment_path = data_root / experiment_name
    path = next(experiment_path.glob('*_{}'.format(flist_id)))
    assert path.is_dir(), 'Folder {} for ID {} not found.'.format(path, _id)
