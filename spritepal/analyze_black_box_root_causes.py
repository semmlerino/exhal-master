#!/usr/bin/env python3
"""
Black Box Root Cause Analysis

This script analyzes the existing codebase to identify potential root causes
for black box display issues in the manual offset dialog, focusing on:

1. Threading issues causing stale data display
2. Widget update failures due to timing problems
3. Cache misses and inefficient preview generation
4. Signal/slot connection timing issues
5. Memory pressure causing GC pauses

The analysis is based on code patterns and known Qt/PyQt issues.
"""

import ast
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict, Counter

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.logging_config import get_logger

logger = get_logger(__name__)


class BlackBoxRootCauseAnalyzer:
    """Analyzes code patterns that could cause black box display issues."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.analysis_results = {}
        
        # Code patterns that often cause black box issues
        self.problematic_patterns = {
            'thread_safety': {
                'description': 'Thread safety issues with Qt widgets',
                'patterns': [
                    r'QMetaObject\.invokeMethod.*Qt\.QueuedConnection',
                    r'QThread\.currentThread.*QApplication.*thread',
                    r'\.update\(\).*worker.*thread',
                    r'\.repaint\(\).*thread',
                    r'pixmap.*worker.*thread'
                ],
                'severity': 'HIGH'
            },
            'widget_updates': {
                'description': 'Widget update timing and validation issues', 
                'patterns': [
                    r'setPixmap.*without.*validation',
                    r'\.update\(\).*\.repaint\(\).*processEvents',
                    r'pixmap.*isNull.*check',
                    r'preview_label.*None.*check',
                    r'QPixmap.*QImage.*conversion'
                ],
                'severity': 'HIGH'
            },
            'cache_timing': {
                'description': 'Cache timing and stale data issues',
                'patterns': [
                    r'cache.*hit.*miss.*timing',
                    r'preview_cached.*preview_ready.*ordering',
                    r'debounce.*delay.*stale',
                    r'_current_offset.*race.*condition',
                    r'request_id.*stale.*check'
                ],
                'severity': 'MEDIUM'
            },
            'signal_coordination': {
                'description': 'Signal emission and coordination problems',
                'patterns': [
                    r'emit.*preview_ready.*thread',
                    r'signal.*disconnect.*connect.*timing',
                    r'QueuedConnection.*signal.*delay',
                    r'valueChanged.*sliderMoved.*coordination',
                    r'offset_changed.*preview.*synchronization'
                ],
                'severity': 'MEDIUM'
            },
            'memory_pressure': {
                'description': 'Memory allocation and garbage collection issues',
                'patterns': [
                    r'large.*allocation.*preview',
                    r'memory.*leak.*pixmap',
                    r'gc\.collect.*performance',
                    r'bytearray.*tile_data.*memory',
                    r'PIL.*Image.*memory.*usage'
                ],
                'severity': 'LOW'
            }
        }
        
        # Files to analyze
        self.key_files = [
            'ui/dialogs/manual_offset_unified_integrated.py',
            'ui/common/smart_preview_coordinator.py', 
            'ui/common/preview_worker_pool.py',
            'ui/widgets/sprite_preview_widget.py',
            'ui/rom_extraction/workers/preview_worker.py'
        ]
    
    def analyze_codebase(self) -> Dict[str, any]:
        """Perform comprehensive root cause analysis of the codebase."""
        logger.info("Starting black box root cause analysis...")
        
        results = {
            'pattern_analysis': {},
            'code_issues': {},
            'risk_assessment': {},
            'recommendations': []
        }
        
        # Analyze each file for problematic patterns
        for file_path in self.key_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                logger.info(f"Analyzing: {file_path}")
                file_results = self._analyze_file(full_path)
                results['pattern_analysis'][file_path] = file_results
        
        # Identify specific code issues
        results['code_issues'] = self._identify_specific_issues()
        
        # Assess overall risk
        results['risk_assessment'] = self._assess_risk_factors(results['pattern_analysis'])
        
        # Generate recommendations
        results['recommendations'] = self._generate_recommendations(results)
        
        return results
    
    def _analyze_file(self, file_path: Path) -> Dict[str, any]:
        """Analyze a single file for problematic patterns."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            file_results = {
                'total_lines': len(content.splitlines()),
                'pattern_matches': {},
                'critical_issues': [],
                'threading_concerns': [],
                'performance_concerns': []
            }
            
            # Check for each problematic pattern
            for pattern_name, pattern_info in self.problematic_patterns.items():
                matches = []
                for pattern in pattern_info['patterns']:
                    regex_matches = re.finditer(pattern, content, re.IGNORECASE)
                    for match in regex_matches:
                        line_num = content[:match.start()].count('\n') + 1
                        matches.append({
                            'line': line_num,
                            'pattern': pattern,
                            'text': match.group(0),
                            'context': self._get_line_context(content, line_num)
                        })
                
                file_results['pattern_matches'][pattern_name] = {
                    'count': len(matches),
                    'severity': pattern_info['severity'],
                    'description': pattern_info['description'],
                    'matches': matches
                }
            
            # Specific analysis for known black box issues
            file_results = self._analyze_specific_issues(content, file_results, file_path.name)
            
            return file_results
            
        except Exception as e:
            logger.error(f"Error analyzing {file_path}: {e}")
            return {'error': str(e)}
    
    def _get_line_context(self, content: str, line_num: int, context_lines: int = 2) -> List[str]:
        """Get context lines around a specific line number."""
        lines = content.splitlines()
        start = max(0, line_num - context_lines - 1)
        end = min(len(lines), line_num + context_lines)
        return lines[start:end]
    
    def _analyze_specific_issues(self, content: str, file_results: Dict, filename: str) -> Dict:
        """Analyze specific known issues that cause black boxes."""
        
        # Issue 1: Thread safety in sprite widget updates
        if 'sprite_preview_widget.py' in filename:
            if 'QThread.currentThread()' in content and 'setPixmap' in content:
                thread_safety_checks = len(re.findall(r'QThread\.currentThread.*main_thread', content))
                if thread_safety_checks < 3:  # Should have multiple checks
                    file_results['critical_issues'].append({
                        'type': 'THREAD_SAFETY',
                        'severity': 'HIGH',
                        'description': 'Insufficient thread safety checks for widget updates',
                        'evidence': f'Only {thread_safety_checks} thread safety checks found'
                    })
        
        # Issue 2: Pixmap validation failures
        pixmap_sets = len(re.findall(r'setPixmap\([^)]+\)', content))
        pixmap_validations = len(re.findall(r'pixmap.*isNull|pixmap.*None', content))
        if pixmap_sets > 0 and pixmap_validations / pixmap_sets < 0.5:
            file_results['critical_issues'].append({
                'type': 'PIXMAP_VALIDATION',
                'severity': 'HIGH',
                'description': 'Insufficient pixmap validation before display',
                'evidence': f'{pixmap_sets} setPixmap calls, {pixmap_validations} validations'
            })
        
        # Issue 3: Signal timing and coordination
        if 'smart_preview_coordinator.py' in filename or 'manual_offset' in filename:
            signal_emissions = len(re.findall(r'\.emit\(', content))
            queued_connections = len(re.findall(r'Qt\.ConnectionType\.QueuedConnection', content))
            if signal_emissions > 5 and queued_connections == 0:
                file_results['critical_issues'].append({
                    'type': 'SIGNAL_TIMING',
                    'severity': 'MEDIUM',
                    'description': 'Signals without QueuedConnection may cause timing issues',
                    'evidence': f'{signal_emissions} signal emissions, {queued_connections} queued connections'
                })
        
        # Issue 4: Cache invalidation timing
        if 'coordinator' in filename or 'cache' in filename:
            cache_hits = len(re.findall(r'cache.*hit', content, re.IGNORECASE))
            cache_invalidations = len(re.findall(r'cache.*clear|cache.*invalidate', content, re.IGNORECASE))
            if cache_hits > 0 and cache_invalidations == 0:
                file_results['performance_concerns'].append({
                    'type': 'CACHE_INVALIDATION',
                    'severity': 'MEDIUM',
                    'description': 'Cache without proper invalidation may serve stale data',
                    'evidence': f'{cache_hits} cache references, {cache_invalidations} invalidations'
                })
        
        # Issue 5: Memory allocation patterns
        large_allocations = len(re.findall(r'bytearray\([^)]*1024[^)]*1024|bytes\([^)]*MB', content, re.IGNORECASE))
        if large_allocations > 2:
            file_results['performance_concerns'].append({
                'type': 'MEMORY_ALLOCATION',
                'severity': 'LOW',
                'description': 'Large memory allocations may cause GC pauses',
                'evidence': f'{large_allocations} large allocation patterns found'
            })
        
        return file_results
    
    def _identify_specific_issues(self) -> Dict[str, any]:
        """Identify specific code issues based on known black box patterns."""
        issues = {
            'critical_bugs': [],
            'performance_bottlenecks': [],
            'design_issues': [],
            'threading_problems': []
        }
        
        # Analyze the main dialog for critical issues
        dialog_file = self.project_root / 'ui/dialogs/manual_offset_unified_integrated.py'
        if dialog_file.exists():
            with open(dialog_file, 'r') as f:
                dialog_content = f.read()
            
            # Check for the critical issue: preview requests without proper coordination
            if '_on_offset_changed' in dialog_content:
                # Look for the specific pattern that causes black boxes
                coordinator_request_pattern = r'_smart_preview_coordinator.*request_preview'
                if not re.search(coordinator_request_pattern, dialog_content):
                    issues['critical_bugs'].append({
                        'file': 'manual_offset_unified_integrated.py',
                        'function': '_on_offset_changed',
                        'issue': 'Missing preview request in offset change handler',
                        'severity': 'CRITICAL',
                        'description': 'Offset changes may not trigger preview updates',
                        'line_pattern': '_on_offset_changed.*offset_changed.emit',
                        'fix_suggestion': 'Add coordinator.request_preview(offset) in _on_offset_changed'
                    })
        
        # Check preview widget for display issues
        widget_file = self.project_root / 'ui/widgets/sprite_preview_widget.py'
        if widget_file.exists():
            with open(widget_file, 'r') as f:
                widget_content = f.read()
            
            # Check for proper pixmap validation
            if 'load_sprite_from_4bpp' in widget_content:
                validation_patterns = [
                    r'pixmap.*isNull\(\)',
                    r'pixmap is None',
                    r'preview_label.*None'
                ]
                
                validation_count = sum(len(re.findall(pattern, widget_content)) for pattern in validation_patterns)
                if validation_count < 3:
                    issues['critical_bugs'].append({
                        'file': 'sprite_preview_widget.py',
                        'function': 'load_sprite_from_4bpp',
                        'issue': 'Insufficient pixmap validation',
                        'severity': 'HIGH',
                        'description': 'Invalid pixmaps may cause black box display',
                        'validation_count': validation_count,
                        'fix_suggestion': 'Add comprehensive pixmap validation before setPixmap'
                    })
        
        # Check coordinator for timing issues
        coordinator_file = self.project_root / 'ui/common/smart_preview_coordinator.py'
        if coordinator_file.exists():
            with open(coordinator_file, 'r') as f:
                coordinator_content = f.read()
            
            # Check for proper debounce timing
            debounce_values = re.findall(r'debounce.*=.*(\d+)', coordinator_content)
            if debounce_values:
                max_debounce = max(int(val) for val in debounce_values)
                if max_debounce > 200:  # >200ms debounce is too slow
                    issues['performance_bottlenecks'].append({
                        'file': 'smart_preview_coordinator.py',
                        'issue': 'Excessive debounce delay',
                        'severity': 'MEDIUM',
                        'description': f'Debounce delay of {max_debounce}ms may cause slow updates',
                        'fix_suggestion': 'Reduce debounce delay to 50-100ms for better responsiveness'
                    })
        
        return issues
    
    def _assess_risk_factors(self, pattern_analysis: Dict) -> Dict[str, any]:
        """Assess overall risk factors for black box issues."""
        risk_assessment = {
            'overall_risk': 'UNKNOWN',
            'primary_concerns': [],
            'risk_factors': {},
            'confidence_score': 0.0
        }
        
        # Count issues by severity
        severity_counts = defaultdict(int)
        total_issues = 0
        
        for file_path, file_analysis in pattern_analysis.items():
            if 'error' in file_analysis:
                continue
                
            for pattern_name, pattern_results in file_analysis.get('pattern_matches', {}).items():
                severity = pattern_results['severity']
                count = pattern_results['count']
                severity_counts[severity] += count
                total_issues += count
        
        # Calculate risk score
        risk_score = (
            severity_counts['HIGH'] * 3 +
            severity_counts['MEDIUM'] * 2 +
            severity_counts['LOW'] * 1
        )
        
        if risk_score >= 10:
            risk_assessment['overall_risk'] = 'HIGH'
            risk_assessment['confidence_score'] = 0.9
        elif risk_score >= 5:
            risk_assessment['overall_risk'] = 'MEDIUM'  
            risk_assessment['confidence_score'] = 0.7
        else:
            risk_assessment['overall_risk'] = 'LOW'
            risk_assessment['confidence_score'] = 0.5
        
        # Identify primary concerns
        if severity_counts['HIGH'] > 2:
            risk_assessment['primary_concerns'].append('Thread safety and widget update issues')
        if severity_counts['MEDIUM'] > 3:
            risk_assessment['primary_concerns'].append('Signal timing and cache coordination problems')
        if total_issues > 10:
            risk_assessment['primary_concerns'].append('Multiple minor issues may compound')
        
        risk_assessment['risk_factors'] = {
            'high_severity_issues': severity_counts['HIGH'],
            'medium_severity_issues': severity_counts['MEDIUM'], 
            'low_severity_issues': severity_counts['LOW'],
            'total_issues': total_issues,
            'risk_score': risk_score
        }
        
        return risk_assessment
    
    def _generate_recommendations(self, analysis_results: Dict) -> List[Dict[str, str]]:
        """Generate specific recommendations based on analysis."""
        recommendations = []
        
        risk_level = analysis_results['risk_assessment']['overall_risk']
        critical_bugs = analysis_results['code_issues'].get('critical_bugs', [])
        
        # Critical recommendations based on risk level
        if risk_level == 'HIGH':
            recommendations.append({
                'priority': 'CRITICAL',
                'category': 'Thread Safety',
                'action': 'Implement comprehensive thread safety checks for all widget updates',
                'rationale': 'High-risk thread safety issues detected that can cause display failures'
            })
        
        # Specific recommendations based on detected issues
        for bug in critical_bugs:
            if bug.get('severity') == 'CRITICAL':
                recommendations.append({
                    'priority': 'CRITICAL',
                    'category': 'Bug Fix',
                    'action': bug.get('fix_suggestion', 'Fix critical bug'),
                    'rationale': f"{bug.get('description', 'Critical bug detected')} in {bug.get('file', 'unknown file')}"
                })
        
        # General recommendations
        pattern_analysis = analysis_results.get('pattern_analysis', {})
        thread_issues = 0
        cache_issues = 0
        
        for file_analysis in pattern_analysis.values():
            if 'error' in file_analysis:
                continue
            pattern_matches = file_analysis.get('pattern_matches', {})
            thread_issues += pattern_matches.get('thread_safety', {}).get('count', 0)
            cache_issues += pattern_matches.get('cache_timing', {}).get('count', 0)
        
        if thread_issues > 2:
            recommendations.append({
                'priority': 'HIGH',
                'category': 'Threading',
                'action': 'Review and fix all thread safety issues in widget updates',
                'rationale': f'{thread_issues} potential thread safety problems detected'
            })
        
        if cache_issues > 1:
            recommendations.append({
                'priority': 'MEDIUM',
                'category': 'Caching',
                'action': 'Optimize cache timing and implement proper invalidation',
                'rationale': f'{cache_issues} cache-related timing issues detected'
            })
        
        # Always recommend comprehensive testing
        recommendations.append({
            'priority': 'HIGH',
            'category': 'Testing',
            'action': 'Run comprehensive performance profiling to validate fixes',
            'rationale': 'Performance profiling will confirm whether fixes resolve black box issues'
        })
        
        return recommendations
    
    def generate_report(self, analysis_results: Dict) -> str:
        """Generate comprehensive analysis report."""
        lines = [
            "=" * 80,
            "BLACK BOX ROOT CAUSE ANALYSIS REPORT",
            "=" * 80,
            "",
            "EXECUTIVE SUMMARY",
            "-" * 40,
        ]
        
        risk_assessment = analysis_results['risk_assessment']
        lines.extend([
            f"Overall Risk Level: {risk_assessment['overall_risk']}",
            f"Confidence Score: {risk_assessment['confidence_score']*100:.1f}%",
            f"Total Issues Found: {risk_assessment['risk_factors']['total_issues']}",
            f"Critical Issues: {risk_assessment['risk_factors']['high_severity_issues']}",
            ""
        ])
        
        if risk_assessment['primary_concerns']:
            lines.append("Primary Concerns:")
            for concern in risk_assessment['primary_concerns']:
                lines.append(f"  • {concern}")
            lines.append("")
        
        # Critical bugs section
        critical_bugs = analysis_results['code_issues'].get('critical_bugs', [])
        if critical_bugs:
            lines.extend([
                "CRITICAL BUGS IDENTIFIED",
                "-" * 40,
            ])
            
            for i, bug in enumerate(critical_bugs, 1):
                lines.extend([
                    f"{i}. {bug.get('issue', 'Unknown issue')}",
                    f"   File: {bug.get('file', 'Unknown')}",
                    f"   Severity: {bug.get('severity', 'Unknown')}",
                    f"   Description: {bug.get('description', 'No description')}",
                    f"   Fix: {bug.get('fix_suggestion', 'No suggestion')}",
                    ""
                ])
        
        # Pattern analysis summary
        lines.extend([
            "PATTERN ANALYSIS SUMMARY",
            "-" * 40,
        ])
        
        pattern_summary = defaultdict(int)
        for file_analysis in analysis_results['pattern_analysis'].values():
            if 'error' in file_analysis:
                continue
            for pattern_name, pattern_results in file_analysis.get('pattern_matches', {}).items():
                pattern_summary[pattern_name] += pattern_results['count']
        
        for pattern_name, count in pattern_summary.items():
            if count > 0:
                pattern_info = self.problematic_patterns.get(pattern_name, {})
                severity = pattern_info.get('severity', 'UNKNOWN')
                description = pattern_info.get('description', 'No description')
                lines.append(f"{pattern_name}: {count} matches ({severity}) - {description}")
        lines.append("")
        
        # Recommendations
        lines.extend([
            "RECOMMENDATIONS (Priority Order)",
            "-" * 40,
        ])
        
        recommendations = analysis_results.get('recommendations', [])
        for i, rec in enumerate(recommendations, 1):
            priority = rec.get('priority', 'UNKNOWN')
            category = rec.get('category', 'Unknown')
            action = rec.get('action', 'No action specified')
            rationale = rec.get('rationale', 'No rationale provided')
            
            lines.extend([
                f"{i}. [{priority}] {category}: {action}",
                f"   Rationale: {rationale}",
                ""
            ])
        
        # Root cause hypothesis
        lines.extend([
            "ROOT CAUSE HYPOTHESIS",
            "-" * 40,
        ])
        
        if risk_assessment['confidence_score'] > 0.8:
            lines.append("HIGH CONFIDENCE DIAGNOSIS:")
            if critical_bugs:
                primary_bug = critical_bugs[0]
                lines.append(f"  Primary Issue: {primary_bug.get('description', 'Critical bug')}")
                lines.append(f"  Location: {primary_bug.get('file', 'Unknown')} - {primary_bug.get('function', 'Unknown function')}")
                lines.append(f"  Impact: Black boxes displayed instead of sprites due to {primary_bug.get('issue', 'unknown issue')}")
            else:
                lines.append("  Multiple high-severity issues contributing to display failures")
        elif risk_assessment['confidence_score'] > 0.6:
            lines.append("MODERATE CONFIDENCE:")
            lines.append("  Likely cause is combination of thread safety and timing issues")
            lines.append("  Recommend focused investigation on widget update patterns")
        else:
            lines.append("LOW CONFIDENCE:")
            lines.append("  Multiple potential causes identified")
            lines.append("  Comprehensive performance profiling needed for definitive diagnosis")
        
        lines.extend([
            "",
            "NEXT STEPS",
            "-" * 40,
            "1. Fix critical bugs identified above",
            "2. Run performance profiler to validate fixes",
            "3. Test with rapid slider movements to confirm black box resolution",
            "4. Monitor for any remaining display issues",
            "",
            "=" * 80
        ])
        
        return "\n".join(lines)


def main():
    """Main entry point for root cause analysis."""
    analyzer = BlackBoxRootCauseAnalyzer()
    
    print("Analyzing SpritePal codebase for black box root causes...")
    print("This may take a few moments...\n")
    
    try:
        # Perform comprehensive analysis
        results = analyzer.analyze_codebase()
        
        # Generate and display report
        report = analyzer.generate_report(results)
        print(report)
        
        # Save report to file
        output_file = Path("black_box_analysis_report.txt")
        with open(output_file, 'w') as f:
            f.write(report)
        
        print(f"\nDetailed analysis saved to: {output_file}")
        
        # Return appropriate exit code based on risk level
        risk_level = results['risk_assessment']['overall_risk']
        if risk_level == 'HIGH':
            return 2  # High risk
        elif risk_level == 'MEDIUM':
            return 1  # Medium risk
        else:
            return 0  # Low risk
            
    except Exception as e:
        print(f"Error during analysis: {e}")
        return 3


if __name__ == "__main__":
    sys.exit(main())