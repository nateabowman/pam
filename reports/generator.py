"""
Report generation for World P.A.M.
"""

from typing import Dict, Any, List
from datetime import datetime
from logger import get_logger


class ReportGenerator:
    """Generates reports in various formats."""
    
    def __init__(self):
        self.logger = get_logger("reports")
    
    def generate_json_report(self, data: Dict[str, Any]) -> str:
        """Generate JSON report."""
        import json
        return json.dumps(data, indent=2, default=str)
    
    def generate_csv_report(self, data: List[Dict[str, Any]]) -> str:
        """Generate CSV report."""
        import csv
        import io
        
        if not data:
            return ""
        
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
        
        return output.getvalue()
    
    def generate_text_report(self, title: str, sections: Dict[str, str]) -> str:
        """Generate plain text report."""
        report = f"{title}\n{'=' * len(title)}\n\n"
        report += f"Generated: {datetime.utcnow().isoformat()}Z\n\n"
        
        for section_title, content in sections.items():
            report += f"{section_title}\n{'-' * len(section_title)}\n{content}\n\n"
        
        return report

