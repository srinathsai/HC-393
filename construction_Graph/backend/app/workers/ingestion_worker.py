import sys
import os

# Add parent directories to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# CORRECT IMPORTS - Matching your actual structure
from app.database.neo4j_client import Neo4jClient
from app.database.vector_store import VectorStore
from app.services.entity_extractor import EntityExtractor
from app.config import get_settings, get_chroma_directory
import fitz  # PyMuPDF
from io import BytesIO
from openai import OpenAI
import gc  # ADDED: For memory management

settings = get_settings()

def process_document(filepath: str, doc_id: str, filename: str):
    """
    🔥 MEMORY-EFFICIENT + DIMENSION-FIXED + PAGE-TRACKED: Process document safely
    """
    
    print("\n" + "="*80)
    print(f"⚡ PROCESSING: {filename}")
    print(f"🆔 Doc ID: {doc_id}")
    print("="*80 + "\n")
    
    try:
        # Step 1: Initialize services
        print("🔧 Step 1: Initializing services...")
        
        chroma_dir = get_chroma_directory()
        print(f"   📂 ChromaDB path: {chroma_dir}")
        
        neo4j_client = Neo4jClient(
            uri=settings.neo4j_uri,
            user=settings.neo4j_user,
            password=settings.neo4j_password
        )
        
        vector_store = VectorStore(
            persist_directory=chroma_dir,
            collection_name="construction_docs"
        )
        
        entity_extractor = EntityExtractor(
            openai_api_key=settings.openai_api_key,
            model=settings.openai_model
        )
        
        openai_client = OpenAI(api_key=settings.openai_api_key)
        
        print("   ✅ All services ready\n")
        
        # Step 2: Open PDF
        print("📖 Step 2: PDF Processing...")
        print("   📄 Opening PDF...")
        
        pdf_document = fitz.open(filepath)
        page_count = len(pdf_document)
        print(f"   📊 Found {page_count} pages")
        
        # 🔥 CRITICAL: SMALL batches to prevent memory buildup
        batch_size = 2  # REDUCED from 4 to 2 for safety
        num_batches = (page_count + batch_size - 1) // batch_size
        print(f"   🔄 Processing in {num_batches} batches of {batch_size} pages each...\n")
        
        # 🔥 NEW: Track chunks with page numbers
        all_chunks_with_pages = []  # List of (chunk_text, page_number) tuples
        all_entities = []
        all_relationships = []
        
        # Process each batch separately to avoid memory buildup
        for batch_idx in range(num_batches):
            start_page = batch_idx * batch_size
            end_page = min(start_page + batch_size, page_count)
            
            print(f"   ⚙️ Batch {batch_idx + 1}/{num_batches}: pages {start_page + 1}-{end_page}...")
            
            # Extract text for THIS batch only - WITH PAGE TRACKING
            batch_pages_text = []  # List of (page_text, page_number)
            for page_num in range(start_page, end_page):
                page = pdf_document[page_num]
                page_text = page.get_text()
                batch_pages_text.append((page_text, page_num + 1))  # Store with 1-based page number
            
            # Combine text for entity extraction
            batch_text_combined = ""
            for page_text, page_num in batch_pages_text:
                batch_text_combined += f"\n--- Page {page_num} ---\n{page_text}"
            
            # 🔥 MEMORY FIX: Chunk each page separately to track page numbers
            batch_chunks_count = 0
            for page_text, page_num in batch_pages_text:
                if len(page_text.strip()) > 50:  # Only chunk if page has content
                    page_chunks = entity_extractor.chunk_text(
                        page_text, 
                        chunk_size=800,
                        overlap=150
                    )
                    
                    # Store chunks with their page number
                    for chunk in page_chunks:
                        all_chunks_with_pages.append((chunk, page_num))
                        batch_chunks_count += 1
                        
                        # Safety limit per batch
                        if batch_chunks_count >= 50:
                            break
                
                if batch_chunks_count >= 50:
                    break
            
            # Extract entities from THIS batch only
            batch_entities = []
            batch_rels = []
            
            if len(batch_text_combined.strip()) > 100:
                batch_entities, batch_rels = entity_extractor.extract_text_entities(
                    batch_text_combined, doc_id, filename
                )
                all_entities.extend(batch_entities)
                all_relationships.extend(batch_rels)
            
            print(f"      ✅ Batch {batch_idx + 1} complete: {batch_chunks_count} chunks, {len(batch_entities)} entities")
            
            # 🔥 CRITICAL: Clear batch data and force garbage collection
            del batch_pages_text
            del batch_text_combined
            del batch_entities
            del batch_rels
            gc.collect()
        
        print(f"\n   ✅ Text extraction complete: {page_count} pages")
        print(f"   ✅ Total chunks: {len(all_chunks_with_pages)}")
        print(f"   ✅ Total entities: {len(all_entities)}, relationships: {len(all_relationships)}\n")
        
        # Step 3: Create embeddings
        print("🔗 Step 3: Creating vector embeddings...")
        
        # 🔥 FIX #2: USE CONSISTENT EMBEDDING MODEL
        # CRITICAL: Must match what's stored in ChromaDB
        embedding_model = "text-embedding-3-small"  # 1536 dimensions
        print(f"   🎯 Using model: {embedding_model} (1536 dimensions)")
        
        vector_chunks = []
        
        # Process embeddings in SMALL batches
        embedding_batch_size = 20  # REDUCED from 50
        
        for i in range(0, len(all_chunks_with_pages), embedding_batch_size):
            batch = all_chunks_with_pages[i:i + embedding_batch_size]
            
            for idx, (chunk, page_num) in enumerate(batch):
                global_idx = i + idx
                
                try:
                    # Generate embedding with CORRECT model
                    embedding_response = openai_client.embeddings.create(
                        model=embedding_model,  # FIXED: Consistent model
                        input=chunk[:8000]  # Limit input size
                    )
                    embedding = embedding_response.data[0].embedding
                    
                    # Verify dimension
                    if len(embedding) != 1536:
                        print(f"      ⚠️ WARNING: Unexpected embedding dimension: {len(embedding)}")
                        continue
                    
                    # 🔥 FIX #3: Create vector point WITH CORRECT PAGE NUMBER
                    vector_chunks.append({
                        'id': f"{doc_id}_chunk_{global_idx}",
                        'vector': embedding,
                        'payload': {
                            'doc_id': doc_id,
                            'filename': filename,
                            'page': page_num,  # ✅ FIXED: Real page number!
                            'chunk_index': global_idx,
                            'text': chunk[:2000],  # Limit stored text
                            'is_diagram': False
                        }
                    })
                    
                except Exception as e:
                    print(f"      ⚠️ Embedding error for chunk {global_idx}: {e}")
                    continue
            
            print(f"   ✅ Embedded batch {i//embedding_batch_size + 1}/{(len(all_chunks_with_pages) + embedding_batch_size - 1)//embedding_batch_size}")
            
            # Force garbage collection after each batch
            gc.collect()
        
        print(f"   ✅ Created {len(vector_chunks)} vector points\n")
        
        # Step 4: Vision extraction (only first 3 pages to save memory)
        print(f"🔍 Step 4: Vision extraction (first 3 pages)...")
        
        vision_entities = []
        vision_relationships = []
        pages_for_vision = list(range(min(3, page_count)))
        
        for page_num in pages_for_vision:
            print(f"   📸 Processing page {page_num + 1}...")
            
            try:
                page = pdf_document[page_num]
                mat = fitz.Matrix(2, 2)
                pix = page.get_pixmap(matrix=mat)
                img_bytes = pix.tobytes("png")
                
                result = entity_extractor.extract_diagram_entities(img_bytes, page_num + 1, doc_id)
                
                page_entities = result.get('entities', [])
                page_relationships = result.get('relationships', [])
                
                vision_entities.extend(page_entities)
                vision_relationships.extend(page_relationships)
                
                print(f"      ✅ Page {page_num + 1}: {len(page_entities)} entities, {len(page_relationships)} rels")
                
                # Free memory
                del img_bytes
                del pix
                gc.collect()
                
            except Exception as e:
                print(f"      ⚠️ Vision error on page {page_num + 1}: {e}")
        
        pdf_document.close()
        print(f"   ✅ Vision complete: {len(vision_entities)} entities total\n")
        
        # Step 5: BM25 indexing
        print("📇 Step 5: BM25 indexing...")
        
        try:
            from app.database.bm25_index import BM25Index
            
            # Create BM25 index
            bm25_index = BM25Index(persist_dir=chroma_dir)
            
            # Prepare metadata for BM25 WITH CORRECT PAGE NUMBERS
            chunks_only = [chunk for chunk, page in all_chunks_with_pages]
            bm25_metadata = [
                {
                    'id': f"{doc_id}_chunk_{i}",
                    'doc_id': doc_id,
                    'filename': filename,
                    'page': all_chunks_with_pages[i][1],  # ✅ Real page number
                    'chunk_index': i,
                    'is_diagram': False
                }
                for i in range(len(all_chunks_with_pages))
            ]
            
            # Add to BM25 index
            bm25_index.add(chunks_only, bm25_metadata)
            
            print(f"   ✅ BM25 indexed {len(chunks_only)} chunks\n")
            
        except Exception as e:
            print(f"   ⚠️ BM25 indexing failed (non-critical): {e}\n")
        
        # Step 6: Save to Neo4j
        print("🕸️ Step 6: Saving to Neo4j...")
        
        combined_entities = all_entities + vision_entities
        combined_relationships = all_relationships + vision_relationships
        
        print(f"   📊 Total entities: {len(combined_entities)}")
        print(f"   📊 Total relationships: {len(combined_relationships)}")
        
        if combined_entities:
            saved = neo4j_client.save_entities(combined_entities, doc_id=doc_id)
            print(f"   ✅ Neo4j: {saved} entities saved")
        
        if combined_relationships:
            saved = neo4j_client.save_relationships(combined_relationships)
            print(f"   ✅ Neo4j: {saved} relationships saved\n")
        
        # Step 7: Save to ChromaDB in batches
        print("💾 Step 7: Saving to ChromaDB...")
        print(f"   📊 Vector points to save: {len(vector_chunks)}")
        
        if not vector_chunks:
            print("   ❌ NO VECTORS TO SAVE!")
            raise ValueError("No vectors generated")
        
        # Save in SMALL batches
        saved_total = 0
        save_batch_size = 50  # REDUCED from 100
        
        for i in range(0, len(vector_chunks), save_batch_size):
            batch = vector_chunks[i:i + save_batch_size]
            
            try:
                saved = vector_store.upsert_vectors(batch, batch_size=50)
                saved_total += saved
                print(f"   ✅ Saved batch {i//save_batch_size + 1}/{(len(vector_chunks) + save_batch_size - 1)//save_batch_size}")
            except Exception as e:
                print(f"   ⚠️ Batch save error: {e}")
                continue
            
            # Force garbage collection
            gc.collect()
        
        print(f"   ✅ ChromaDB: {saved_total} vectors saved\n")
        
        # Final cleanup
        del all_chunks_with_pages
        del all_entities
        del all_relationships
        del vector_chunks
        gc.collect()
        
        print("="*80)
        print("✅ PROCESSING COMPLETE!")
        print("="*80 + "\n")
        
        return {
            'status': 'success',
            'chunks': saved_total,
            'entities': len(combined_entities),
            'relationships': len(combined_relationships),
            'vectors': saved_total
        }
        
    except Exception as e:
        print("\n" + "="*80)
        print(f"❌ PROCESSING FAILED: {e}")
        print("="*80 + "\n")
        
        import traceback
        traceback.print_exc()
        
        raise Exception(f"Processing failed: {e}")

if __name__ == "__main__":
    test_file = "path/to/your/test.pdf"
    test_doc_id = "test-doc-123"
    test_filename = "test.pdf"
    
    result = process_document(test_file, test_doc_id, test_filename)
    print(f"\n✅ Result: {result}")