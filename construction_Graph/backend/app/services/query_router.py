import re
from typing import Dict, Any, Optional

class QueryRouter:
    def __init__(self):
        self.patterns = {
            'references': re.compile(r'(reference|references|refer)\s+([A-Z]-?\d{2,4})', re.IGNORECASE),
            'sheet_lookup': re.compile(r'(?:sheet|drawing)\s+([A-Z]-?\d{2,4})', re.IGNORECASE),
            'zone_components': re.compile(r'(?:component|equipment).*?(?:zone|area)\s+(\w+)', re.IGNORECASE),
            'component_location': re.compile(r'where.*?([A-Z]{1,3}-\d{2,4})', re.IGNORECASE),
            'on_sheet': re.compile(r'(?:on|in)\s+sheet\s+([A-Z]-?\d{2,4})', re.IGNORECASE),
            'detail_callout': re.compile(r'(?:detail|see)\s+(\d+)\s*/\s*([A-Z]-?\d{2,4})', re.IGNORECASE),
        }

    def route(self, question: str) -> Dict[str, Any]:
        route = self._check_structural_patterns(question)
        if route:
            return route
        return {'type': 'hybrid', 'reason': 'Complex query requiring semantic search and reasoning'}

    def _check_structural_patterns(self, question: str) -> Optional[Dict[str, Any]]:
        m = self.patterns['references'].search(question)
        if m:
            return {'type': 'cypher', 'template': 'find_references', 'params': {'sheet_id': m.group(2)}}

        m = self.patterns['zone_components'].search(question)
        if m:
            return {'type': 'cypher', 'template': 'find_components_in_zone', 'params': {'zone': m.group(1)}}

        m = self.patterns['component_location'].search(question)
        if m:
            return {'type': 'cypher', 'template': 'find_component_location', 'params': {'tag': m.group(1)}}

        m = self.patterns['on_sheet'].search(question)
        if m:
            return {'type': 'cypher', 'template': 'list_on_sheet', 'params': {'sheet_id': m.group(1)}}

        m = self.patterns['detail_callout'].search(question)
        if m:
            return {'type': 'cypher', 'template': 'detail_jump', 'params': {'detail': m.group(1), 'sheet_id': m.group(2)}}

        return None

    def build_cypher_query(self, template: str, params: Dict[str, Any]) -> str:
        templates = {
            'find_references': """
                MATCH (target:Drawing {sheetId: $sheet_id})
                MATCH (referrer:Drawing)-[:REFERENCES]->(target)
                RETURN referrer.sheetId AS sheetId, referrer.title AS title
                LIMIT 200
            """,
            'find_components_in_zone': """
                MATCH (z:Location {zone: $zone})
                MATCH (z)-[:CONTAINS*1..2]->(c:Component)
                RETURN c.tag AS tag, c.type AS type, c.discipline AS discipline
                LIMIT 200
            """,
            'find_component_location': """
                MATCH (c:Component {tag: $tag})-[:LOCATED_IN]->(l:Location)
                RETURN c.tag AS component, l.room AS room, l.floor AS floor, l.building AS building
                LIMIT 10
            """,
            'list_on_sheet': """
                MATCH (d:Drawing {sheetId: $sheet_id})-[:CONTAINS*0..2]->(c:Component)
                RETURN c.tag AS tag, c.type AS type, c.discipline AS discipline
                LIMIT 200
            """,
            'detail_jump': """
                MATCH (d:Drawing {sheetId: $sheet_id})
                RETURN $detail AS detail, d.sheetId AS sheetId, d.title AS title
                LIMIT 1
            """,
        }
        return templates.get(template, "")
