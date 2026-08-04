import pytest
from app import gitstore
from app.gitstore import GitStoreError


@pytest.fixture()
def repo(tmp_path, monkeypatch):
    path = tmp_path / "git_repo"
    monkeypatch.setattr(gitstore, "GIT_REPO_PATH", path)
    gitstore.init_repo()
    return path


def test_write_then_read_roundtrip(repo):
    commit_hash = gitstore.write_policy_file("tenant-1", "policy.cedar", "permit(principal, action, resource);", "alice")
    assert commit_hash
    assert gitstore.read_policy_file("tenant-1", "policy.cedar") == "permit(principal, action, resource);"


def test_read_missing_file_raises(repo):
    with pytest.raises(GitStoreError, match="not found"):
        gitstore.read_policy_file("tenant-1", "nope.cedar")


def test_delete_removes_file(repo):
    gitstore.write_policy_file("tenant-1", "policy.cedar", "permit(principal, action, resource);", "alice")
    gitstore.delete_policy_file("tenant-1", "policy.cedar", "alice")
    with pytest.raises(GitStoreError):
        gitstore.read_policy_file("tenant-1", "policy.cedar")


def test_path_traversal_filename_rejected(repo):
    with pytest.raises(GitStoreError, match="Invalid filename"):
        gitstore.write_policy_file("tenant-1", "../../etc/passwd", "malicious", "attacker")


def test_slash_in_filename_rejected(repo):
    with pytest.raises(GitStoreError, match="Invalid filename"):
        gitstore.write_policy_file("tenant-1", "sub/dir/file.cedar", "content", "attacker")


def test_tenant_isolation_on_disk(repo):
    gitstore.write_policy_file("tenant-1", "policy.cedar", "content-1", "alice")
    gitstore.write_policy_file("tenant-2", "policy.cedar", "content-2", "bob")
    assert gitstore.read_policy_file("tenant-1", "policy.cedar") == "content-1"
    assert gitstore.read_policy_file("tenant-2", "policy.cedar") == "content-2"