from typing import Optional, List, Dict, Any, Type, TypeVar
from beanie import Document
from pymongo.errors import DuplicateKeyError


T = TypeVar("T", bound=Document)


class DatabaseFacade:
    def __init__(self, model_class: Type[T]):
        self.model_class = model_class

    async def create(self, **kwargs) -> T:
        """Create a new document"""
        try:
            instance = self.model_class(**kwargs)
            return await instance.create()
        except DuplicateKeyError:
            raise ValueError("Document with unique field already exists")

    async def get_by_id(self, doc_id: str) -> Optional[T]:
        """Get document by ID"""
        try:
            return await self.model_class.get(doc_id)
        except Exception:
            return None

    async def get_one(self, **filters) -> Optional[T]:
        """Get single document by filters"""
        return await self.model_class.find_one(filters)

    async def get_many(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        skip: Optional[int] = None,
        sort: Optional[List[tuple]] = None,
    ) -> List[T]:
        """Get multiple documents with optional filtering, pagination and sorting"""
        query = self.model_class.find(filters or {})

        if skip:
            query = query.skip(skip)
        if limit:
            query = query.limit(limit)
        if sort:
            query = query.sort(sort)

        return await query.to_list()

    async def update_by_id(self, doc_id: str, **updates) -> Optional[T]:
        """Update document by ID"""
        document = await self.get_by_id(doc_id)
        if not document:
            return None

        for key, value in updates.items():
            setattr(document, key, value)

        await document.save()
        return document

    async def update_one(self, filters: Dict[str, Any], **updates) -> Optional[T]:
        """Update single document by filters"""
        document = await self.get_one(**filters)
        if not document:
            return None

        for key, value in updates.items():
            setattr(document, key, value)

        await document.save()
        return document

    async def delete_by_id(self, doc_id: str) -> bool:
        """Delete document by ID"""
        document = await self.get_by_id(doc_id)
        if not document:
            return False

        await document.delete()
        return True

    async def delete_one(self, **filters) -> bool:
        """Delete single document by filters"""
        document = await self.get_one(**filters)
        if not document:
            return False

        await document.delete()
        return True

    async def delete_many(self, **filters) -> int:
        """Delete multiple documents by filters"""
        documents = await self.get_many(filters)
        count = 0
        for doc in documents:
            await doc.delete()
            count += 1
        return count

    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count documents matching filters"""
        if filters:
            return await self.model_class.find(filters).count()
        else:
            return await self.model_class.count()

    async def exists(self, **filters) -> bool:
        """Check if document exists"""
        return await self.get_one(**filters) is not None
