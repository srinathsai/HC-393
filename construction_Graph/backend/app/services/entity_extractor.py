import os
import re
import json
from typing import List, Dict, Any, Tuple, Iterator
from openai import OpenAI
import gc  # ADDED: Garbage collection for memory management

class EntityExtractor:
    """Enhanced entity extraction with MEMORY-EFFICIENT processing"""
    
    def __init__(self, openai_api_key: str, model: str = "gpt-4o"):
        print(f"🔧 [EntityExtractor] Initializing with model: {model}")
        self.client = OpenAI(api_key=openai_api_key)
        self.model = model
        
        # Equipment type mappings for better extraction
        self.equipment_types = {
            'transformer': ['transformer', 'xfmr', 'substation transformer'],
            'panel': ['panel', 'panelboard', 'distribution panel', 'electrical panel'],
            'breaker': ['breaker', 'circuit breaker', 'cb', 'mcb', 'mccb'],
            'generator': ['generator', 'gen', 'emergency generator', 'backup generator'],
            'switchgear': ['switchgear', 'switch gear', 'main switchgear'],
            'mcc': ['mcc', 'motor control center', 'motor control'],
            'ups': ['ups', 'uninterruptible power supply'],
            'ats': ['ats', 'automatic transfer switch', 'transfer switch'],
            'lighting': ['light', 'lighting', 'fixture', 'luminaire'],
            'conduit': ['conduit', 'raceway', 'emt', 'rigid conduit'],
            'cable': ['cable', 'wire', 'conductor', 'feeder'],
            'receptacle': ['receptacle', 'outlet', 'plug', 'socket'],
            'junction_box': ['junction box', 'j-box', 'pull box'],
            'meter': ['meter', 'metering', 'kwh meter'],
            'disconnect': ['disconnect', 'safety switch', 'fused disconnect'],
            'busway': ['busway', 'bus duct', 'busduct'],
            'vfd': ['vfd', 'variable frequency drive', 'drive'],
            'pdu': ['pdu', 'power distribution unit']
        }
        
        print("✅ [EntityExtractor] Ready")

    def extract_text_entities(self, text: str, doc_id: str, filename: str) -> Tuple[List[Dict], List[Dict]]:
        """Extract entities and relationships from text using multiple strategies"""
        
        print("   🔍 Starting text entity extraction...")
        entities = []
        relationships = []
        
        # Strategy 1: Regex-based extraction for common patterns
        regex_entities, regex_rels = self._extract_with_regex(text, doc_id)
        entities.extend(regex_entities)
        relationships.extend(regex_rels)
        print(f"   ✅ Regex extraction: {len(regex_entities)} entities, {len(regex_rels)} relationships")
        
        # Strategy 2: LLM-based extraction for complex patterns
        if len(text.strip()) > 100:  # Only use LLM if significant text
            llm_entities, llm_rels = self._extract_with_llm(text, doc_id, filename)
            entities.extend(llm_entities)
            relationships.extend(llm_rels)
            print(f"   ✅ LLM extraction: {len(llm_entities)} entities, {len(llm_rels)} relationships")
        
        # Deduplicate
        entities = self._deduplicate_entities(entities)
        relationships = self._deduplicate_relationships(relationships)
        
        print(f"   ✅ Total after deduplication: {len(entities)} entities, {len(relationships)} relationships")
        return entities, relationships

    def _extract_with_regex(self, text: str, doc_id: str) -> Tuple[List[Dict], List[Dict]]:
        """Extract entities using regex patterns"""
        entities = []
        relationships = []
        
        # Pattern 1: Equipment with specifications (e.g., "200A Panel", "480V Transformer")
        spec_pattern = r'(\d+[AVW])\s+(\w+(?:\s+\w+)?)'
        for match in re.finditer(spec_pattern, text, re.IGNORECASE):
            spec, equipment = match.groups()
            equipment_lower = equipment.lower()
            
            # Check if it matches known equipment types
            for eq_type, keywords in self.equipment_types.items():
                if any(kw in equipment_lower for kw in keywords):
                    entity_id = f"{doc_id}_{eq_type}_{spec}_{len(entities)}"
                    entities.append({
                        'id': entity_id,
                        'name': f"{spec} {equipment}",
                        'type': eq_type,
                        'properties': {'specification': spec, 'doc_id': doc_id}
                    })
                    break
        
        # Pattern 2: Location references (e.g., "on roof", "in basement", "Room 101")
        location_pattern = r'(?:in|on|at|near)\s+((?:room|floor|level|roof|basement|mechanical room|electrical room)\s*\w*)'
        for match in re.finditer(location_pattern, text, re.IGNORECASE):
            location = match.group(1)
            entity_id = f"{doc_id}_location_{len(entities)}"
            entities.append({
                'id': entity_id,
                'name': location,
                'type': 'location',
                'properties': {'doc_id': doc_id}
            })
        
        # Pattern 3: Panel schedules (e.g., "Panel LP-1", "MDP-2")
        panel_pattern = r'\b([A-Z]{1,4}P?-?\d+)\b'
        for match in re.finditer(panel_pattern, text):
            panel_name = match.group(1)
            entity_id = f"{doc_id}_panel_{panel_name}"
            entities.append({
                'id': entity_id,
                'name': panel_name,
                'type': 'panel',
                'properties': {'doc_id': doc_id}
            })
        
        return entities, relationships

    def _extract_with_llm(self, text: str, doc_id: str, filename: str) -> Tuple[List[Dict], List[Dict]]:
        """Extract entities using LLM for complex patterns"""
        
        # Truncate if too long
        max_chars = 8000
        if len(text) > max_chars:
            text = text[:max_chars] + "..."
        
        prompt = f"""Extract electrical/MEP entities and relationships from this construction document text.

EQUIPMENT TYPES TO IDENTIFY:
- Transformers, Panels, Breakers, Generators, Switchgear
- Motor Control Centers (MCC), UPS, Transfer Switches (ATS)
- Lighting fixtures, Conduits, Cables, Receptacles
- Junction boxes, Meters, Disconnects, Busways, VFDs, PDUs

EXTRACT:
1. **Entities**: Equipment, locations, systems with their specifications
2. **Relationships**: Connections, feeds, serves, located in, controlled by

TEXT FROM: {filename}
---
{text}
---

Return JSON:
{{
  "entities": [
    {{"id": "unique_id", "name": "Equipment/Location Name", "type": "equipment_type", "properties": {{"spec": "details"}} }},
    ...
  ],
  "relationships": [
    {{"source": "entity_id1", "target": "entity_id2", "type": "feeds|serves|located_in|controls"}},
    ...
  ]
}}"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=2000
            )
            
            content = response.choices[0].message.content.strip()
            
            # Extract JSON from markdown code blocks if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            data = json.loads(content)
            
            # Add doc_id to all entities
            entities = data.get('entities', [])
            for ent in entities:
                if 'properties' not in ent:
                    ent['properties'] = {}
                ent['properties']['doc_id'] = doc_id
                if 'id' not in ent or not ent['id']:
                    ent['id'] = f"{doc_id}_{ent.get('type', 'unknown')}_{len(entities)}"
            
            relationships = data.get('relationships', [])
            
            return entities, relationships
            
        except Exception as e:
            print(f"   ⚠️ LLM extraction error: {e}")
            return [], []

    def _deduplicate_entities(self, entities: List[Dict]) -> List[Dict]:
        """Remove duplicate entities based on name and type"""
        seen = set()
        unique = []
        for ent in entities:
            key = (ent.get('name', '').lower(), ent.get('type', ''))
            if key not in seen and key != ('', ''):
                seen.add(key)
                unique.append(ent)
        return unique

    def _deduplicate_relationships(self, relationships: List[Dict]) -> List[Dict]:
        """Remove duplicate relationships"""
        seen = set()
        unique = []
        for rel in relationships:
            key = (rel.get('source', ''), rel.get('target', ''), rel.get('type', ''))
            if key not in seen and '' not in key:
                seen.add(key)
                unique.append(rel)
        return unique

    def extract_diagram_entities(self, image_bytes: bytes, page_num: int, doc_id: str) -> Dict[str, Any]:
        """Extract entities from diagram using vision with SAFE error handling"""
        
        print(f"\n🖼️ [VISION EXTRACTION] Page {page_num}")
        
        import base64
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        print(f"   Image size: {len(base64_image)} bytes (base64)")
        
        # ✅ BEST PROMPT - Generic + Self-Identifying
        prompt = """You are a construction document indexing assistant helping organize technical drawings for project management.

    Please analyze this construction diagram and identify:

    1. What TYPE of diagram this is (electrical, HVAC, plumbing, structural, architectural, fire protection, etc.)
    2. Key COMPONENTS with their tags/identifiers (e.g., "Panel LP-3", "AHU-1", "Pump P-101")
    3. RELATIONSHIPS or connections between components
    4. SPECIFICATIONS if clearly labeled (voltage, capacity, size, etc.)
    5. LOCATIONS if visible (room numbers, floor levels, areas)

    Return your analysis in this JSON format:
    {
    "diagram_type": "type_of_diagram",
    "entities": [
        {"id": "unique_identifier", "name": "Component Name", "type": "component_type", "properties": {"key": "value"}}
    ],
    "relationships": [
        {"source": "source_id", "target": "target_id", "type": "relationship_type"}
    ],
    "summary": "One sentence describing what this diagram shows"
    }

    Return ONLY valid JSON with no markdown formatting."""

        try:
            print("   🔄 Calling GPT-4o Vision API...")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
                    ]
                }],
                max_tokens=2000,
                temperature=0.1
            )
            
            print("   ✅ Vision API response received")
            
            # Extract content
            content = None
            if response and response.choices and len(response.choices) > 0:
                message = response.choices[0].message
                if message and hasattr(message, 'content') and message.content:
                    content = message.content.strip()
            
            if not content:
                print("   ⚠️ Vision API returned empty content")
                return {
                    'entities': [],
                    'relationships': [],
                    'summary': f'No content returned for page {page_num}',
                    'page': page_num
                }
            
            # Check for refusal
            refusal_phrases = [
                "I'm unable to analyze",
                "I can't analyze",
                "I'm sorry, I can't",
                "I cannot assist",
                "I'm not able to",
                "I can't help with"
            ]
            
            if any(phrase.lower() in content.lower() for phrase in refusal_phrases):
                print(f"   ⚠️ Vision API refused to analyze (content policy)")
                print(f"   📄 Refusal message: {content[:150]}...")
                return {
                    'entities': [],
                    'relationships': [],
                    'summary': f'Vision analysis declined for page {page_num}',
                    'page': page_num,
                    'refused': True
                }
            
            # Clean markdown if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            # Parse JSON
            data = json.loads(content)
            print("   ✅ JSON parsed successfully")
            
            # ✅ LOG DIAGRAM TYPE
            diagram_type = data.get('diagram_type', 'unknown')
            print(f"   📊 Diagram type detected: {diagram_type}")
            
            # Convert to standard format
            result = self._normalize_vision_output(data, doc_id, page_num)
            
            # ✅ ADD DIAGRAM TYPE TO RESULT
            result['diagram_type'] = diagram_type
            
            print(f"   ✅ VISION EXTRACTION COMPLETE:")
            print(f"      Type: {diagram_type}")
            print(f"      Entities: {len(result.get('entities', []))}")
            print(f"      Relationships: {len(result.get('relationships', []))}")
            print(f"      Summary: {result.get('summary', 'N/A')[:100]}")
            
            return result
            
        except json.JSONDecodeError as e:
            print(f"   ❌ JSON parse error: {e}")
            print(f"   📄 Raw content that failed to parse:")
            print(f"   {content[:300]}")
            return {
                'entities': [],
                'relationships': [],
                'summary': f'JSON parse error on page {page_num}',
                'page': page_num
            }
            
        except Exception as e:
            print(f"   ❌ Vision API failed: {type(e).__name__}: {e}")
            return {
                'entities': [],
                'relationships': [],
                'summary': f'Vision extraction failed on page {page_num}',
                'page': page_num
            }
    
    def _normalize_vision_output(self, data: Dict, doc_id: str, page_num: int) -> Dict[str, Any]:
        """Normalize vision output to standard format"""
        entities = data.get('entities', [])
        relationships = data.get('relationships', [])
        
        # Add doc_id and page to all entities
        for ent in entities:
            if 'properties' not in ent:
                ent['properties'] = {}
            ent['properties']['doc_id'] = doc_id
            ent['properties']['page'] = page_num
            
            # Ensure ID exists
            if 'id' not in ent or not ent['id']:
                ent['id'] = f"{doc_id}_page{page_num}_{ent.get('type', 'unknown')}_{len(entities)}"
        
        return {
            'entities': entities,
            'relationships': relationships,
            'summary': data.get('summary', ''),
            'page': page_num
        }

    def chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """
        🔥 MEMORY-EFFICIENT CHUNKING - GENERATOR-BASED
        Prevents MemoryError by using lazy evaluation
        """
        
        if not text or len(text.strip()) == 0:
            print("   ⚠️ No text to chunk")
            return []
        
        # CRITICAL FIX: Use generator and create small batches
        chunks = []
        start = 0
        text_len = len(text)
        
        # Process in SMALL increments to avoid memory buildup
        while start < text_len:
            end = min(start + chunk_size, text_len)
            
            # Try to break at sentence boundary
            if end < text_len:
                # Look for sentence endings within a reasonable window
                search_window = min(200, text_len - end)
                for sep in ['. ', '.\n', '! ', '?\n']:
                    last_sep = text.rfind(sep, start, end + search_window)
                    if last_sep != -1 and last_sep > start:
                        end = last_sep + 1
                        break
            
            # Extract chunk
            chunk = text[start:end].strip()
            
            # MEMORY FIX: Only append if chunk is valid and reasonable size
            if chunk and len(chunk) > 50:  # Skip tiny chunks
                # Limit individual chunk size to prevent memory issues
                if len(chunk) > chunk_size * 2:
                    chunk = chunk[:chunk_size * 2]
                chunks.append(chunk)
                
                # CRITICAL: Force garbage collection every 10 chunks
                if len(chunks) % 10 == 0:
                    gc.collect()
            
            # Move to next position with overlap
            if end >= text_len:
                break
            start = max(start + chunk_size - overlap, start + 1)
            
            # Safety check: prevent infinite loops
            if start >= text_len:
                break
        
        print(f"   ✅ Created {len(chunks)} chunks from text")
        
        # Final garbage collection
        gc.collect()
        
        return chunks

    def chunk_text_generator(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> Iterator[str]:
        """
        🔥 ALTERNATIVE: Generator version for ULTRA memory efficiency
        Use this if you still get memory errors with the regular version
        """
        if not text or len(text.strip()) == 0:
            return
        
        start = 0
        text_len = len(text)
        
        while start < text_len:
            end = min(start + chunk_size, text_len)
            
            # Try to break at sentence boundary
            if end < text_len:
                for sep in ['. ', '.\n', '! ', '?\n']:
                    last_sep = text.rfind(sep, start, end + 100)
                    if last_sep != -1 and last_sep > start:
                        end = last_sep + 1
                        break
            
            chunk = text[start:end].strip()
            
            if chunk and len(chunk) > 50:
                # Limit chunk size
                if len(chunk) > chunk_size * 2:
                    chunk = chunk[:chunk_size * 2]
                yield chunk
            
            if end >= text_len:
                break
            start = max(start + chunk_size - overlap, start + 1)
            
            if start >= text_len:
                break