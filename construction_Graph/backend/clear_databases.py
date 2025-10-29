# clear_databases.py
"""
Clear all data from ChromaDB and Neo4j for fresh start
Run this before demo/testing to start with clean databases
"""

import chromadb
from chromadb.config import Settings
from neo4j import GraphDatabase
from pathlib import Path

# Configuration - UPDATE THESE PATHS
CHROMA_DIR = r"C:\chroma\construction_graph"  # From your startup logs
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "construction123"

def clear_chromadb():
    """Clear ChromaDB by deleting and recreating collection"""
    print("🧹 Clearing ChromaDB...")
    
    try:
        client = chromadb.PersistentClient(
            path=CHROMA_DIR,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Delete collections
        try:
            client.delete_collection("construction_docs")
            print("  ✅ Deleted 'construction_docs' collection")
        except Exception as e:
            print(f"  ⚠️  Collection might not exist: {e}")
        
        try:
            client.delete_collection("construction_images")
            print("  ✅ Deleted 'construction_images' collection")
        except:
            pass
        
        # Recreate empty collections
        client.get_or_create_collection(
            name="construction_docs",
            metadata={"hnsw:space": "cosine"}
        )
        print("  ✅ Created fresh 'construction_docs' collection")
        
        client.get_or_create_collection(
            name="construction_images",
            metadata={"hnsw:space": "cosine"}
        )
        print("  ✅ Created fresh 'construction_images' collection")
        
        # Clear BM25 index
        bm25_file = Path(CHROMA_DIR) / "bm25_index.pkl"
        if bm25_file.exists():
            bm25_file.unlink()
            print("  ✅ Deleted BM25 index")
        
        # Clear embedding cache
        cache_file = Path(CHROMA_DIR) / "emb_cache.sqlite"
        if cache_file.exists():
            cache_file.unlink()
            print("  ✅ Deleted embedding cache")
        
        print("✅ ChromaDB cleared successfully\n")
        return True
        
    except Exception as e:
        print(f"❌ ChromaDB clear failed: {e}\n")
        return False

def clear_neo4j():
    """Clear all nodes and relationships from Neo4j"""
    print("🧹 Clearing Neo4j...")
    
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        
        with driver.session() as session:
            # Count before
            result = session.run("MATCH (n) RETURN count(n) as count")
            before_count = result.single()["count"]
            print(f"  📊 Found {before_count} nodes")
            
            result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
            before_rels = result.single()["count"]
            print(f"  📊 Found {before_rels} relationships")
            
            # Delete everything
            session.run("MATCH (n) DETACH DELETE n")
            print("  ✅ Deleted all nodes and relationships")
            
            # Verify
            result = session.run("MATCH (n) RETURN count(n) as count")
            after_count = result.single()["count"]
            print(f"  ✅ Neo4j now has {after_count} nodes")
        
        driver.close()
        print("✅ Neo4j cleared successfully\n")
        return True
        
    except Exception as e:
        print(f"❌ Neo4j clear failed: {e}")
        print("  💡 Make sure Neo4j is running\n")
        return False

def verify_empty():
    """Verify databases are empty"""
    print("🔍 Verifying databases are empty...")
    
    try:
        # Check ChromaDB
        client = chromadb.PersistentClient(path=CHROMA_DIR)
        collection = client.get_collection("construction_docs")
        count = collection.count()
        
        if count == 0:
            print("  ✅ ChromaDB is empty (0 vectors)")
        else:
            print(f"  ⚠️  ChromaDB still has {count} vectors")
        
        # Check Neo4j
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        with driver.session() as session:
            result = session.run("MATCH (n) RETURN count(n) as count")
            count = result.single()["count"]
            
            if count == 0:
                print("  ✅ Neo4j is empty (0 nodes)")
            else:
                print(f"  ⚠️  Neo4j still has {count} nodes")
        
        driver.close()
        print()
        
    except Exception as e:
        print(f"❌ Verification failed: {e}\n")

def main():
    print("="*60)
    print("🗑️  Database Cleanup Utility")
    print("="*60)
    print("\n⚠️  This will DELETE ALL DATA from ChromaDB and Neo4j!")
    print(f"ChromaDB: {CHROMA_DIR}")
    print(f"Neo4j: {NEO4J_URI}\n")
    
    response = input("Type 'yes' to continue: ")
    
    if response.lower() != "yes":
        print("❌ Cancelled.")
        return
    
    print("\n" + "="*60)
    
    chroma_success = clear_chromadb()
    neo4j_success = clear_neo4j()
    verify_empty()
    
    print("="*60)
    if chroma_success and neo4j_success:
        print("✅ All databases cleared!")
        print("\n📝 Next: Restart API server and upload fresh documents")
    else:
        print("⚠️  Some operations failed. Check errors above.")
    print("="*60)

if __name__ == "__main__":
    main()