import unittest

from src.infrastructure.persistence.mongo.documents import IDENTITY_DOCUMENT_MODELS


class ModelRegistryTests(unittest.TestCase):
    def test_identity_document_models_count(self) -> None:
        self.assertEqual(len(IDENTITY_DOCUMENT_MODELS), 5)


if __name__ == "__main__":
    unittest.main()
