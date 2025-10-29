import sys
import os
from pathlib import Path

print("="*60)
print("Testing Database Connections")
print("="*60)

# Load environment
from dotenv import load_dotenv
load_dotenv()

# Test 1: ChromaDB
print("\n1. Testing ChromaDB...")
try:
    import chromadb
    from chromadb.config import Settings
    
    chroma_dir = r"C:\chroma\construction_graph"
    Path(chroma_dir).mkdir(parents=True, exist_ok=True)
    
    client = chromadb.PersistentClient(
        path=chroma_dir,
        settings=Settings(anonymized_telemetry=False, allow_reset=True)
    )
    
    collection = client.get_or_create_collection(
        name="construction_docs",
        metadata={"hnsw:space": "cosine"}
    )
    
    # Test write
    collection.add(
        ids=["test1"],
        embeddings=[[0.1] * 3072],
        documents=["test document"],
        metadatas=[{"test": True}]
    )
    
    count = collection.count()
    print(f"   ✅ ChromaDB: {count} vectors (test write successful)")
    
    # Clean up test
    collection.delete(ids=["test1"])
    
except Exception as e:
    print(f"   ❌ ChromaDB FAILED: {e}")
    sys.exit(1)

# Test 2: Neo4j
print("\n2. Testing Neo4j...")
try:
    from neo4j import GraphDatabase
    
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "construction123")
    
    driver = GraphDatabase.driver(uri, auth=(user, password))
    driver.verify_connectivity()
    
    # Test write
    with driver.session() as session:
        session.run("CREATE (n:Test {name: 'test'}) RETURN n")
        result = session.run("MATCH (n:Test) RETURN count(n) as count")
        count = result.single()["count"]
        print(f"   ✅ Neo4j: {count} test nodes (write successful)")
        
        # Clean up test
        session.run("MATCH (n:Test) DELETE n")
    
    driver.close()
    
except Exception as e:
    print(f"   ❌ Neo4j FAILED: {e}")
    print(f"   Check if Neo4j is running: docker ps | findstr neo4j")
    sys.exit(1)

# Test 3: OpenAI
print("\n3. Testing OpenAI API...")
try:
    from openai import OpenAI
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key.startswith("sk-..."):
        raise ValueError("Invalid OpenAI API key in .env file!")
    
    client = OpenAI(api_key=api_key)
    
    response = client.embeddings.create(
        input="test",
        model="text-embedding-3-large"
    )
    
    dim = len(response.data[0].embedding)
    print(f"   ✅ OpenAI: {dim} dimensions (API working)")
    
except Exception as e:
    print(f"   ❌ OpenAI FAILED: {e}")
    print(f"   Check your OPENAI_API_KEY in .env file")
    sys.exit(1)

# Test 4: Redis
print("\n4. Testing Redis...")
try:
    from redis import Redis
    
    r = Redis(host='localhost', port=6379, decode_responses=True)
    r.ping()
    
    # Test write
    r.set("test_key", "test_value")
    value = r.get("test_key")
    r.delete("test_key")
    
    print(f"   ✅ Redis: Connected (write/read successful)")
    
except Exception as e:
    print(f"   ❌ Redis FAILED: {e}")
    print(f"   Check if Redis is running: docker ps | findstr redis")
    sys.exit(1)

print("\n" + "="*60)
print("✅ ALL DATABASE TESTS PASSED!")
print("="*60)
print("\nYour system is ready. You can now:")
print("1. Start the API server")
print("2. Start the RQ worker")
print("3. Upload documents")