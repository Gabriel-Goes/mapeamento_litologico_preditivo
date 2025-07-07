import unittest
from unittest.mock import patch, MagicMock

from mapgeo import databaseengine

class DatabaseEngineTest(unittest.TestCase):
    def setUp(self):
        databaseengine.DatabaseEngine._instance = None

    def test_engine_and_session_singleton(self):
        fake_engine = MagicMock(name="engine")
        fake_session = MagicMock(name="session")

        sessionmaker_instance = MagicMock(return_value=fake_session)

        with patch('mapgeo.databaseengine.create_engine', return_value=fake_engine) as ce, \
             patch('mapgeo.databaseengine.sessionmaker', return_value=sessionmaker_instance) as sm, \
             patch.object(databaseengine.Base.metadata, 'create_all') as create_all:
            engine = databaseengine.DatabaseEngine.get_engine()
            session = databaseengine.DatabaseEngine.get_session()

        ce.assert_called_once_with(databaseengine.url)
        create_all.assert_called_once_with(fake_engine)
        sm.assert_called_once_with(bind=fake_engine)
        sessionmaker_instance.assert_called_once_with()
        self.assertIs(engine, fake_engine)
        self.assertIs(session, fake_session)

if __name__ == '__main__':
    unittest.main()
