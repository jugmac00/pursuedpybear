import gc
import time

import pytest

from ppb import GameEngine, BaseScene
import ppb.events
import ppb.assetlib
from ppb.assetlib import DelayedThreadExecutor, Asset, AssetLoadingSystem
from ppb.testutils import Failer


class AssetTestScene(BaseScene):
    def on_asset_loaded(self, event, signal):
        self.ale = event
        signal(ppb.events.Quit())


def test_executor():
    # Can't easily test the cancellation, since jobs in progress can't be cancelled.
    def work():
        return "spam"

    pool = DelayedThreadExecutor()
    assert not pool._threads

    fut = pool.submit(work)
    time.sleep(0.01)  # Let any hypothetical threads do work
    assert not pool._threads
    assert not (fut.done() or fut.running())

    with pool:
        assert fut.result() == "spam"

    assert pool._shutdown


def test_loading():
    a = Asset('ppb/engine.py')
    engine = GameEngine(
        AssetTestScene, basic_systems=[AssetLoadingSystem, Failer],
        fail=lambda e: False, message=None, run_time=1,
    )
    with engine:
        engine.start()
        ats = engine.current_scene

        engine.main_loop()

        assert a.load()
        print(vars(ats))
        assert ats.ale.asset is a
        assert ats.ale.total_loaded == 1
        assert ats.ale.total_queued == 0


# def test_loading_root():
#     a = Asset(...)  # TODO: find a cross-platform target in $VENV/bin
#     engine = GameEngine(BaseScene, basic_systems=[AssetLoadingSystem])
#     with engine:
#         engine.start()

#         assert a.load()


def test_missing_package():
    a = Asset('does/not/exist')
    engine = GameEngine(
        AssetTestScene, basic_systems=[AssetLoadingSystem, Failer],
        fail=lambda e: False, message=None, run_time=1,
    )
    with engine:
        engine.start()

        with pytest.raises(FileNotFoundError):
            assert a.load()


def test_missing_resource():
    a = Asset('ppb/dont.touch.this')
    engine = GameEngine(
        AssetTestScene, basic_systems=[AssetLoadingSystem, Failer],
        fail=lambda e: False, message=None, run_time=1,
    )
    with engine:
        engine.start()

        with pytest.raises(FileNotFoundError):
            assert a.load()


def test_parsing():
    class Const(Asset):
        def background_parse(self, data):
            return "nah"

    a = Const('ppb/flags.py')
    engine = GameEngine(
        AssetTestScene, basic_systems=[AssetLoadingSystem, Failer],
        fail=lambda e: False, message=None, run_time=1,
    )
    with engine:
        engine.start()

        assert a.load() == "nah"


def test_missing_parse():
    class Const(Asset):
        def file_missing(self):
            return "igotu"

    a = Const('spam/eggs')
    engine = GameEngine(
        AssetTestScene, basic_systems=[AssetLoadingSystem, Failer],
        fail=lambda e: False, message=None, run_time=1,
    )
    with engine:
        engine.start()

        assert a.load() == "igotu"


def test_instance_condense():
    class SubAsset(Asset):
        pass

    a1 = Asset('ppb/engine.py')
    a2 = Asset('ppb/engine.py')

    a3 = Asset('ppb/scenes.py')

    s1 = SubAsset('ppb/engine.py')

    assert a1 is a2
    assert a1 is not a3
    assert a1 is not s1


def test_free(clean_assets):
    free_called = False

    class Const(Asset):
        def background_parse(self, data):
            return "yoink"

        def free(self, obj):
            nonlocal free_called
            free_called = True

    a = Const('ppb/utils.py')
    engine = GameEngine(
        AssetTestScene, basic_systems=[AssetLoadingSystem, Failer],
        fail=lambda e: False, message=None, run_time=1,
    )
    with engine:
        engine.start()

        assert a.load() == "yoink"
        # At this poiint, background processing should have finished

    del engine, a  # Clean up everything that might be holding a reference.
    gc.collect()
    assert free_called
