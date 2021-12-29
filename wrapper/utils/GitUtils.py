from typing import Optional, List

from git import Repo, Remote, InvalidGitRepositoryError, FetchInfo

from wrapper.utils.ConstantConfig import ConstantConfig
from wrapper.utils.ExeLog import logger


# SDK Documentation : https://gitpython.readthedocs.io/en/stable/index.html

# Utility class between exegol and the Git SDK
class GitUtils:

    def __init__(self):
        """Init git local repository object / SDK"""
        path: str = ConstantConfig.root_path
        logger.debug(f"Loading git at {path}")
        self.__gitRepo: Optional[Repo] = None
        self.__gitRemote: Optional[Remote] = None
        self.__fetchBranchInfo: Optional[FetchInfo] = None
        try:
            self.__gitRepo = Repo(path)
            logger.debug("Git repository successfully loaded")
            logger.success(f"Current git branch : {self.getCurrentBranch()}")
            if len(self.__gitRepo.remotes) > 0:
                self.__gitRemote = self.__gitRepo.remotes['origin']
            else:
                logger.warning("No remote git origin found on repository")
                logger.debug(self.__gitRepo.remotes)
        except InvalidGitRepositoryError:
            logger.warning("Error while loading local git repository. Skipping all git operation.")

    def getCurrentBranch(self) -> str:
        """Get current git branch name"""
        return str(self.__gitRepo.active_branch)

    def listBranch(self) -> List[str]:
        """Return a list of str of all remote git branch available"""
        result = []
        if self.__gitRemote is None:
            return result
        for branch in self.__gitRemote.fetch():
            result.append(branch.name.split('/')[1])
        return result

    def safeCheck(self) -> bool:
        """Check the status of the local git repository,
        if there is pending change it is not safe to apply some operations"""
        if self.__gitRepo is None:
            return False
        if self.__gitRepo.is_dirty():
            logger.warning("Local git have unsaved change. Skipping operation.")
        return not self.__gitRepo.is_dirty()

    def isUpToDate(self, branch: Optional[str] = None) -> bool:
        """Check if the local git repository is up-to-date.
        This method compare the last commit local and remote first,
        if this commit don't match, check the last 15 previous commit (for dev use cases)."""
        if branch is None:
            branch = self.getCurrentBranch()
        # Get last local commit
        current_commit = self.__gitRepo.heads[branch].commit
        # Get last remote commit
        fetch_result = self.__gitRemote.fetch()
        self.__fetchBranchInfo = fetch_result[f'{self.__gitRemote}/{branch}']

        logger.debug(f"Fetch flags : {self.__fetchBranchInfo.flags}")
        logger.debug(f"Fetch note : {self.__fetchBranchInfo.note}")
        logger.debug(f"Fetch old commit : {self.__fetchBranchInfo.old_commit}")
        logger.debug(f"Fetch remote path : {self.__fetchBranchInfo.remote_ref_path}")
        # Bit check to detect flags info
        if self.__fetchBranchInfo.flags & FetchInfo.HEAD_UPTODATE != 0:
            logger.debug("HEAD UP TO DATE flag detected")
        if self.__fetchBranchInfo.flags & FetchInfo.FAST_FORWARD != 0:
            logger.debug("FAST FORWARD flag detected")
        if self.__fetchBranchInfo.flags & FetchInfo.ERROR != 0:
            logger.debug("ERROR flag detected")
        if self.__fetchBranchInfo.flags & FetchInfo.FORCED_UPDATE != 0:
            logger.debug("FORCED_UPDATE flag detected")
        if self.__fetchBranchInfo.flags & FetchInfo.REJECTED != 0:
            logger.debug("REJECTED flag detected")
        if self.__fetchBranchInfo.flags & FetchInfo.NEW_TAG != 0:
            logger.debug("NEW TAG flag detected")

        remote_commit = self.__fetchBranchInfo.commit
        # Check if remote_commit is an ancestor of the last local commit (check if there is local commit ahead)
        return self.__gitRepo.is_ancestor(remote_commit, current_commit)

    def update(self) -> bool:
        """Update local git repository within current branch"""
        if not self.safeCheck():
            return False
        if self.isUpToDate():
            logger.info("Git branch is already up-to-date.")
            return False
        if self.__gitRemote is not None:
            logger.info(f"Updating local git '{self.getCurrentBranch()}'")
            self.__gitRemote.pull()  # TODO need some test, check fast-forward only / try catch ?
            logger.success("Git successfully updated")
            return True
        return False

    def checkout(self, branch: str) -> bool:
        """Change local git branch"""
        if not self.safeCheck():
            return False
        if branch == self.getCurrentBranch():
            logger.warning(f"Branch '{branch}' is already the current branch")
            return False
        self.__gitRepo.heads[branch].checkout()
        logger.success(f"Git successfully checkout to '{branch}'")
        return True