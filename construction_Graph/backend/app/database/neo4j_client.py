from neo4j import GraphDatabase
import logging

logger = logging.getLogger(__name__)


class Neo4jClient:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        logger.info(f"✅ Neo4j connected: {uri}")

    def close(self):
        self.driver.close()

    def get_stats(self):
        """Get database statistics"""
        with self.driver.session() as session:
            # Count nodes
            result = session.run("MATCH (n) RETURN count(n) as count")
            total_nodes = result.single()["count"]

            # Count relationships
            result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
            total_relationships = result.single()["count"]

            # Count documents (unique doc_ids)
            result = session.run("""
                MATCH (n)
                WHERE n.doc_id IS NOT NULL
                RETURN count(DISTINCT n.doc_id) as count
            """)
            total_documents = result.single()["count"]

            return {
                "total_nodes": total_nodes,
                "total_relationships": total_relationships,
                "total_documents": total_documents
            }

    def simple_search(self, query: str, limit: int = 10):
        """Simple text-based search in Neo4j"""
        with self.driver.session() as session:
            cypher = """
            MATCH (n)
            WHERE any(prop IN keys(n) WHERE toString(n[prop]) CONTAINS $search_term)
            RETURN n
            LIMIT $limit
            """
            results = session.run(cypher, search_term=query, limit=limit)
            
            facts = []
            for record in results:
                node = record["n"]
                # Format node as text
                props = dict(node)
                text = f"{list(node.labels)[0] if node.labels else 'Node'}: "
                text += ", ".join([f"{k}={v}" for k, v in props.items() if k != 'doc_id'])
                facts.append({"text": text, "node_id": node.id})
            
            logger.info(f"🕸️ Neo4j search: {len(facts)} facts found")
            return facts

    def get_subgraph(self, entity_names: list, max_depth: int = 2):
        """
        Get nodes and relationships for specific entities.
        Returns (nodes, edges) for graph visualization.
        """
        with self.driver.session() as session:
            # Find nodes matching entity names
            cypher = """
            MATCH (n)
            WHERE any(prop IN keys(n) WHERE toString(n[prop]) IN $entity_names)
            WITH n
            LIMIT 20
            MATCH path = (n)-[r*0..2]-(connected)
            WITH nodes(path) as pathNodes, relationships(path) as pathRels
            UNWIND pathNodes as node
            WITH collect(DISTINCT node) as allNodes, pathRels
            UNWIND pathRels as rel
            RETURN allNodes, collect(DISTINCT rel) as allRels
            """
            
            try:
                result = session.run(cypher, entity_names=entity_names)
                record = result.single()
                
                if not record:
                    return [], []
                
                nodes = []
                for node in record["allNodes"][:30]:  # Limit to 30 nodes
                    props = dict(node)
                    nodes.append({
                        "id": str(node.id),
                        "label": list(node.labels)[0] if node.labels else "Node",
                        "properties": {k: v for k, v in props.items() if k != 'doc_id'}
                    })
                
                edges = []
                for rel in record["allRels"][:50]:  # Limit to 50 edges
                    edges.append({
                        "source": str(rel.start_node.id),
                        "target": str(rel.end_node.id),
                        "type": rel.type
                    })
                
                logger.info(f"📊 Subgraph: {len(nodes)} nodes, {len(edges)} edges")
                return nodes, edges
                
            except Exception as e:
                logger.error(f"Subgraph extraction failed: {e}")
                return [], []

    def get_overview_graph(self, limit: int = 20):
        """
        Get a general overview of the graph.
        Returns (nodes, edges) for visualization.
        """
        with self.driver.session() as session:
            cypher = """
            MATCH (n)
            WITH n
            LIMIT $limit
            OPTIONAL MATCH (n)-[r]-(connected)
            RETURN collect(DISTINCT n) as nodes, 
                   collect(DISTINCT r) as rels,
                   collect(DISTINCT connected) as connectedNodes
            """
            
            try:
                result = session.run(cypher, limit=limit)
                record = result.single()
                
                if not record:
                    return [], []
                
                # Combine all nodes
                all_nodes = record["nodes"] + [n for n in record["connectedNodes"] if n is not None]
                
                nodes = []
                seen_ids = set()
                for node in all_nodes:
                    if node and node.id not in seen_ids:
                        seen_ids.add(node.id)
                        props = dict(node)
                        nodes.append({
                            "id": str(node.id),
                            "label": list(node.labels)[0] if node.labels else "Node",
                            "properties": {k: v for k, v in props.items() if k != 'doc_id'}
                        })
                
                edges = []
                for rel in record["rels"]:
                    if rel:
                        edges.append({
                            "source": str(rel.start_node.id),
                            "target": str(rel.end_node.id),
                            "type": rel.type
                        })
                
                logger.info(f"📊 Overview graph: {len(nodes)} nodes, {len(edges)} edges")
                return nodes, edges
                
            except Exception as e:
                logger.error(f"Overview graph failed: {e}")
                return [], []

    def batch_create_nodes(self, entities: list):
        """
        BACKWARD COMPATIBILITY: Create nodes in batch.
        Called by ingestion_worker.py
        """
        return self.save_entities(entities)

    def save_entities(self, entities: list, doc_id: str = None):
        """Save entities to Neo4j with optional doc_id"""
        if not entities:
            return 0

        with self.driver.session() as session:
            count = 0
            for entity in entities:
                try:
                    # Extract entity data
                    name = entity.get("name", "")
                    entity_type = entity.get("type", "Entity")
                    
                    # ✅ FIX: Sanitize spaces in entity type
                    entity_type = entity_type.replace(' ', '_')
                    
                    properties = entity.get("properties", {})
                    
                    # Add doc_id to properties if provided
                    if doc_id:
                        properties["doc_id"] = doc_id
                    
                    # Create node
                    cypher = f"""
                    MERGE (n:{entity_type} {{name: $name}})
                    SET n += $properties
                    RETURN n
                    """
                    session.run(cypher, name=name, properties=properties)
                    count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to save entity {entity.get('name')}: {e}")

            return count

    def save_relationships(self, relationships: list):
        """Save relationships to Neo4j"""
        if not relationships:
            return 0

        with self.driver.session() as session:
            count = 0
            for rel in relationships:
                try:
                    source = rel.get("source", "")
                    target = rel.get("target", "")
                    rel_type = rel.get("type", "RELATED_TO")
                    
                    # ✅ FIX: Sanitize spaces in relationship type
                    rel_type = rel_type.replace(' ', '_').upper()
                    
                    properties = rel.get("properties", {})
                    
                    cypher = f"""
                    MATCH (s {{name: $source}})
                    MATCH (t {{name: $target}})
                    MERGE (s)-[r:{rel_type}]->(t)
                    SET r += $properties
                    RETURN r
                    """
                    session.run(cypher, source=source, target=target, properties=properties)
                    count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to save relationship: {e}")

            return count

    def delete_document(self, doc_id: str):
        """Delete all nodes and relationships for a specific document"""
        with self.driver.session() as session:
            try:
                # Delete nodes with this doc_id
                result = session.run("""
                    MATCH (n)
                    WHERE n.doc_id = $doc_id
                    DETACH DELETE n
                    RETURN count(n) as deleted_count
                """, doc_id=doc_id)
                
                deleted_count = result.single()["deleted_count"]
                logger.info(f"✅ Deleted {deleted_count} nodes for doc_id={doc_id}")
                
                return deleted_count
                
            except Exception as e:
                logger.error(f"Failed to delete document {doc_id}: {e}")
                return 0

    def clear_all(self):
        """⚠️ Delete ALL nodes and relationships from Neo4j"""
        with self.driver.session() as session:
            try:
                # Get counts before deletion
                stats = self.get_stats()
                
                # Delete everything
                session.run("MATCH (n) DETACH DELETE n")
                
                logger.info(f"✅ Cleared Neo4j: {stats['total_nodes']} nodes, {stats['total_relationships']} relationships")
                
                return stats
                
            except Exception as e:
                logger.error(f"Failed to clear Neo4j: {e}")
                raise

    def list_documents(self):
        """List all unique doc_ids in the database"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (n)
                WHERE n.doc_id IS NOT NULL
                RETURN DISTINCT n.doc_id as doc_id, count(n) as node_count
                ORDER BY doc_id
            """)
            
            docs = []
            for record in result:
                docs.append({
                    "doc_id": record["doc_id"],
                    "node_count": record["node_count"]
                })
            
            return docs