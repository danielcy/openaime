import pytest
from aime.base.knowledge import BaseKnowledge, SimpleInMemoryKnowledge


class TestSimpleInMemoryKnowledge:
    """Tests for SimpleInMemoryKnowledge implementation."""

    @pytest.mark.asyncio
    async def test_add_document(self):
        """Test adding a document to the knowledge base."""
        kb = SimpleInMemoryKnowledge()
        content = "This is a test document about artificial intelligence."
        doc_id = await kb.add_document(content)

        assert doc_id is not None
        assert len(doc_id) > 0

    @pytest.mark.asyncio
    async def test_add_document_with_metadata(self):
        """Test adding a document with metadata."""
        kb = SimpleInMemoryKnowledge()
        content = "Document with metadata"
        metadata = {"author": "test", "category": "test"}

        doc_id = await kb.add_document(content, metadata)
        assert doc_id is not None

    @pytest.mark.asyncio
    async def test_get_document(self):
        """Test retrieving a document by ID."""
        kb = SimpleInMemoryKnowledge()
        content = "Test document for retrieval"
        doc_id = await kb.add_document(content)

        retrieved = await kb.get_document(doc_id)
        assert retrieved == content

    @pytest.mark.asyncio
    async def test_get_nonexistent_document(self):
        """Test retrieving a non-existent document."""
        kb = SimpleInMemoryKnowledge()
        assert await kb.get_document("nonexistent_id") is None

    @pytest.mark.asyncio
    async def test_delete_document(self):
        """Test deleting a document."""
        kb = SimpleInMemoryKnowledge()
        content = "Document to be deleted"
        doc_id = await kb.add_document(content)

        assert await kb.delete_document(doc_id) is True
        assert await kb.get_document(doc_id) is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_document(self):
        """Test deleting a non-existent document."""
        kb = SimpleInMemoryKnowledge()
        assert await kb.delete_document("nonexistent_id") is False

    @pytest.mark.asyncio
    async def test_search_relevant_documents(self):
        """Test searching returns relevant documents."""
        kb = SimpleInMemoryKnowledge()

        # Add test documents
        await kb.add_document("Python is a popular programming language for data science.")
        await kb.add_document("JavaScript is a programming language used for web development.")
        await kb.add_document("Machine learning algorithms include regression and classification.")

        # Search for relevant documents
        results = await kb.search("programming language", top_k=2)

        assert len(results) == 2
        assert "Python is a popular programming language" in results[0][0] or "JavaScript is a programming language" in results[0][0]
        assert results[0][1] >= results[1][1]

    @pytest.mark.asyncio
    async def test_search_with_different_top_k(self):
        """Test search with different top_k values."""
        kb = SimpleInMemoryKnowledge()

        for i in range(5):
            await kb.add_document(f"Document {i}: Content about topic {i}")

        results = await kb.search("topic", top_k=3)
        assert len(results) == 3

        results = await kb.search("topic", top_k=10)
        assert len(results) == 5

    @pytest.mark.asyncio
    async def test_empty_knowledge_search(self):
        """Test searching an empty knowledge base returns empty results."""
        kb = SimpleInMemoryKnowledge()
        results = await kb.search("test query")
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_empty_knowledge_get(self):
        """Test getting document from empty knowledge base."""
        kb = SimpleInMemoryKnowledge()
        assert await kb.get_document("any_id") is None

    @pytest.mark.asyncio
    async def test_empty_knowledge_delete(self):
        """Test deleting from empty knowledge base."""
        kb = SimpleInMemoryKnowledge()
        assert await kb.delete_document("any_id") is False

    @pytest.mark.asyncio
    async def test_search_no_relevant_results(self):
        """Test search with no relevant results."""
        kb = SimpleInMemoryKnowledge()

        await kb.add_document("Cats are popular pets.")
        await kb.add_document("Dogs make great companions.")

        results = await kb.search("fish", top_k=2)
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_multiple_operations(self):
        """Test multiple operations in sequence."""
        kb = SimpleInMemoryKnowledge()

        # Add documents
        doc1 = await kb.add_document("First document about AI")
        doc2 = await kb.add_document("Second document about ML")
        doc3 = await kb.add_document("Third document about DL")

        # Verify all documents exist
        assert await kb.get_document(doc1) is not None
        assert await kb.get_document(doc2) is not None
        assert await kb.get_document(doc3) is not None

        # Search
        results = await kb.search("AI", top_k=2)
        assert len(results) >= 1

        # Delete a document
        assert await kb.delete_document(doc2) is True
        assert await kb.get_document(doc2) is None

        # Verify remaining documents
        assert await kb.get_document(doc1) is not None
        assert await kb.get_document(doc3) is not None


class TestBaseKnowledgeAbstractMethods:
    """Test that BaseKnowledge is properly abstract."""

    def test_base_knowledge_is_abstract(self):
        """Test that BaseKnowledge cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseKnowledge()
