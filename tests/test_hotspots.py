from hotspots import Commit, change_coupling, churn, parse_log, rank_hotspots

LOG = "\x00aaa\n\nsrc/a.py\nsrc/b.py\n\x00bbb\n\nsrc/a.py\n\x00ccc\n\nsrc/a.py\nsrc/b.py\nuv.lock\n"


def test_parse_log_returns_one_commit_per_hash_without_lockfiles():
    commits = parse_log(LOG)

    assert commits == (
        Commit("aaa", frozenset({"src/a.py", "src/b.py"})),
        Commit("bbb", frozenset({"src/a.py"})),
        Commit("ccc", frozenset({"src/a.py", "src/b.py"})),
    )


def test_churn_counts_commits_touching_each_file():
    counts = churn(parse_log(LOG))

    assert counts == {"src/a.py": 3, "src/b.py": 2}


def test_rank_hotspots_orders_by_churn_times_size_and_drops_missing_files():
    sizes = {"src/a.py": 10, "src/b.py": 100}

    ranked = rank_hotspots({"src/a.py": 3, "src/b.py": 2, "gone.py": 9}, sizes)

    assert [(h.path, h.score) for h in ranked] == [("src/b.py", 200), ("src/a.py", 30)]


def test_change_coupling_reports_shared_commits_over_mean_revisions():
    pairs = change_coupling(parse_log(LOG), min_shared=2)

    assert [(p.left, p.right, p.shared, p.degree) for p in pairs] == [("src/a.py", "src/b.py", 2, 80)]


def test_change_coupling_ignores_commits_wider_than_the_limit():
    commits = parse_log(LOG)

    assert change_coupling(commits, min_shared=1, max_files=1) == ()
