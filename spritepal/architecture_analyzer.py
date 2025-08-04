#!/usr/bin/env python3
"""
Architecture Analyzer for Manual Offset Dialog Systems.

This script performs static analysis of the two dialog systems to understand
performance and resource usage implications without requiring full initialization.

Analyzes:
1. Code complexity and component count
2. Signal routing architecture  
3. Dependency injection overhead
4. Memory allocation patterns
5. Scalability characteristics
"""

import ast
import os
import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Set, Tuple


@dataclass
class ComponentAnalysis:
    """Analysis results for a component or system."""
    name: str
    file_count: int
    line_count: int
    class_count: int
    method_count: int
    signal_count: int
    timer_count: int
    widget_count: int
    dependency_count: int
    complexity_score: float
    bottlenecks: List[str]
    scaling_factors: Dict[str, str]


class ArchitectureAnalyzer:
    """Analyzes architecture patterns and performance implications."""
    
    def __init__(self, base_path: str):
        self.base_path = base_path
        self.qt_widgets = {
            'QWidget', 'QDialog', 'QMainWindow', 'QTabWidget', 'QVBoxLayout', 
            'QHBoxLayout', 'QGridLayout', 'QLabel', 'QPushButton', 'QLineEdit',
            'QTextEdit', 'QListWidget', 'QTreeWidget', 'QSplitter', 'QStackedWidget'
        }
        self.qt_signals = {'pyqtSignal', 'Signal'}
        self.qt_timers = {'QTimer'}
    
    def analyze_simplified_system(self) -> ComponentAnalysis:
        """Analyze the simplified dialog system."""
        print("Analyzing Simplified Dialog System...")
        
        # Main dialog file
        dialog_file = os.path.join(self.base_path, "ui/dialogs/manual_offset_dialog_simplified.py")
        
        if not os.path.exists(dialog_file):
            return ComponentAnalysis(
                name="Simplified System",
                file_count=0, line_count=0, class_count=0, method_count=0,
                signal_count=0, timer_count=0, widget_count=0, dependency_count=0,
                complexity_score=0.0, bottlenecks=["File not found"], scaling_factors={}
            )
        
        # Analyze the main file
        analysis = self._analyze_file(dialog_file)
        
        # Additional analysis for supporting components
        supporting_files = [
            "ui/components/base/dialog_base.py",
            "ui/components/panels/scan_controls_panel.py", 
            "ui/components/panels/status_panel.py",
            "ui/widgets/sprite_preview_widget.py"
        ]
        
        for file_path in supporting_files:
            full_path = os.path.join(self.base_path, file_path)
            if os.path.exists(full_path):
                file_analysis = self._analyze_file(full_path)
                analysis = self._merge_analysis(analysis, file_analysis)
        
        # Calculate complexity and identify bottlenecks
        complexity_score = self._calculate_complexity_score(analysis)
        bottlenecks = self._identify_architectural_bottlenecks(analysis, "simplified")
        scaling_factors = self._analyze_scaling_factors(analysis, "simplified")
        
        return ComponentAnalysis(
            name="Simplified System",
            file_count=analysis['file_count'],
            line_count=analysis['line_count'], 
            class_count=analysis['class_count'],
            method_count=analysis['method_count'],
            signal_count=analysis['signal_count'],
            timer_count=analysis['timer_count'],
            widget_count=analysis['widget_count'],
            dependency_count=analysis['dependency_count'],
            complexity_score=complexity_score,
            bottlenecks=bottlenecks,
            scaling_factors=scaling_factors
        )
    
    def analyze_modular_system(self) -> ComponentAnalysis:
        """Analyze the modular dialog system."""
        print("Analyzing Modular Dialog System...")
        
        # Modular system directory
        modular_dir = os.path.join(self.base_path, "ui/dialogs/manual_offset")
        
        if not os.path.exists(modular_dir):
            return ComponentAnalysis(
                name="Modular System",
                file_count=0, line_count=0, class_count=0, method_count=0,
                signal_count=0, timer_count=0, widget_count=0, dependency_count=0,
                complexity_score=0.0, bottlenecks=["Directory not found"], scaling_factors={}
            )
        
        # Get all Python files in the modular system
        modular_files = []
        for root, dirs, files in os.walk(modular_dir):
            for file in files:
                if file.endswith('.py') and not file.startswith('__'):
                    modular_files.append(os.path.join(root, file))
        
        # Analyze all modular files
        combined_analysis = {
            'file_count': 0, 'line_count': 0, 'class_count': 0, 'method_count': 0,
            'signal_count': 0, 'timer_count': 0, 'widget_count': 0, 'dependency_count': 0
        }
        
        for file_path in modular_files:
            file_analysis = self._analyze_file(file_path)
            combined_analysis = self._merge_analysis(combined_analysis, file_analysis)
        
        # Calculate complexity and identify bottlenecks
        complexity_score = self._calculate_complexity_score(combined_analysis)
        bottlenecks = self._identify_architectural_bottlenecks(combined_analysis, "modular")
        scaling_factors = self._analyze_scaling_factors(combined_analysis, "modular")
        
        return ComponentAnalysis(
            name="Modular System",
            file_count=combined_analysis['file_count'],
            line_count=combined_analysis['line_count'],
            class_count=combined_analysis['class_count'], 
            method_count=combined_analysis['method_count'],
            signal_count=combined_analysis['signal_count'],
            timer_count=combined_analysis['timer_count'],
            widget_count=combined_analysis['widget_count'],
            dependency_count=combined_analysis['dependency_count'],
            complexity_score=complexity_score,
            bottlenecks=bottlenecks,
            scaling_factors=scaling_factors
        )
    
    def _analyze_file(self, file_path: str) -> Dict:
        """Analyze a single Python file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse AST
            tree = ast.parse(content)
            
            # Count various elements
            analysis = {
                'file_count': 1,
                'line_count': len(content.splitlines()),
                'class_count': 0,
                'method_count': 0,
                'signal_count': 0,
                'timer_count': 0,
                'widget_count': 0,
                'dependency_count': 0
            }
            
            # Walk the AST
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    analysis['class_count'] += 1
                elif isinstance(node, ast.FunctionDef):
                    analysis['method_count'] += 1
                elif isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
                    analysis['dependency_count'] += 1
            
            # Count Qt-specific elements using regex (more reliable for this analysis)
            signal_patterns = r'\b(?:pyqtSignal|Signal)\b'
            timer_patterns = r'\bQTimer\b'
            widget_patterns = r'\b(?:' + '|'.join(self.qt_widgets) + r')\b'
            
            analysis['signal_count'] = len(re.findall(signal_patterns, content))
            analysis['timer_count'] = len(re.findall(timer_patterns, content))
            analysis['widget_count'] = len(re.findall(widget_patterns, content))
            
            return analysis
            
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
            return {
                'file_count': 0, 'line_count': 0, 'class_count': 0, 'method_count': 0,
                'signal_count': 0, 'timer_count': 0, 'widget_count': 0, 'dependency_count': 0
            }
    
    def _merge_analysis(self, analysis1: Dict, analysis2: Dict) -> Dict:
        """Merge two analysis dictionaries."""
        return {
            key: analysis1.get(key, 0) + analysis2.get(key, 0)
            for key in analysis1.keys()
        }
    
    def _calculate_complexity_score(self, analysis: Dict) -> float:
        """Calculate a complexity score based on various metrics."""
        # Weighted complexity score
        weights = {
            'file_count': 0.1,       # More files = harder to understand
            'class_count': 0.2,      # More classes = more complexity
            'method_count': 0.15,    # More methods = more complexity
            'signal_count': 0.25,    # Signals add complexity
            'dependency_count': 0.2, # Dependencies add complexity
            'timer_count': 0.1       # Timers add state complexity
        }
        
        score = 0.0
        for metric, weight in weights.items():
            score += analysis.get(metric, 0) * weight
        
        return score
    
    def _identify_architectural_bottlenecks(self, analysis: Dict, system_type: str) -> List[str]:
        """Identify potential performance bottlenecks based on architecture."""
        bottlenecks = []
        
        # File organization bottlenecks
        if analysis['file_count'] > 10:
            bottlenecks.append(f"High file count ({analysis['file_count']}) increases initialization overhead")
        
        # Class structure bottlenecks
        if analysis['class_count'] > 15:
            bottlenecks.append(f"High class count ({analysis['class_count']}) increases memory usage")
        
        # Signal routing bottlenecks
        if analysis['signal_count'] > 20:
            bottlenecks.append(f"High signal count ({analysis['signal_count']}) may impact responsiveness")
        
        # Timer management bottlenecks
        if analysis['timer_count'] > 5:
            bottlenecks.append(f"Multiple timers ({analysis['timer_count']}) increase event loop overhead")
        
        # Dependency injection overhead
        if analysis['dependency_count'] > 30:
            bottlenecks.append(f"High dependency count ({analysis['dependency_count']}) slows initialization")
        
        # System-specific bottlenecks
        if system_type == "modular":
            if analysis['file_count'] > 8:
                bottlenecks.append("Modular system: Component initialization overhead")
            if analysis['signal_count'] > 15:
                bottlenecks.append("Modular system: Inter-component signal routing overhead")
        else:
            if analysis['method_count'] > 100:
                bottlenecks.append("Simplified system: Monolithic class complexity")
            if analysis['line_count'] > 1000:
                bottlenecks.append("Simplified system: Large file size impacts readability/maintenance")
        
        return bottlenecks
    
    def _analyze_scaling_factors(self, analysis: Dict, system_type: str) -> Dict[str, str]:
        """Analyze how the system scales with different loads."""
        factors = {}
        
        # Large ROM handling
        if analysis['timer_count'] > 3:
            factors['large_roms'] = "Multiple timers may cause delays with large ROM processing"
        else:
            factors['large_roms'] = "Timer usage should scale well with ROM size"
        
        # Preview generation scaling
        if analysis['signal_count'] > 15:
            factors['preview_updates'] = "High signal count may create preview update bottlenecks"
        else:
            factors['preview_updates'] = "Signal architecture should handle preview updates efficiently"
        
        # Memory scaling
        if analysis['widget_count'] > 20:
            factors['memory_usage'] = "High widget count increases base memory usage"
        else:
            factors['memory_usage'] = "Reasonable widget count for good memory efficiency"
        
        # System-specific scaling
        if system_type == "modular":
            factors['modularity'] = "Component isolation provides good scaling for feature additions"
            factors['initialization'] = "Multi-component initialization may be slower but more flexible"
        else:
            factors['modularity'] = "Monolithic design faster to initialize but harder to extend"
            factors['initialization'] = "Single-component initialization should be fast"
        
        return factors
    
    def generate_performance_report(self) -> None:
        """Generate comprehensive performance analysis report."""
        print("Manual Offset Dialog Architecture Analysis")
        print("=" * 60)
        
        # Analyze both systems
        simplified = self.analyze_simplified_system()
        modular = self.analyze_modular_system()
        
        # System comparison
        print(f"\nSYSTEM COMPARISON:")
        print("-" * 40)
        self._print_system_metrics("Simplified", simplified)
        print()
        self._print_system_metrics("Modular", modular)
        
        # Performance implications
        print(f"\nPERFORMANCE IMPLICATIONS:")
        print("-" * 40)
        self._analyze_performance_implications(simplified, modular)
        
        # Resource usage
        print(f"\nRESOURCE USAGE ANALYSIS:")
        print("-" * 40)
        self._analyze_resource_usage(simplified, modular)
        
        # Scalability analysis
        print(f"\nSCALABILITY ANALYSIS:")
        print("-" * 40)
        self._analyze_scalability(simplified, modular)
        
        # Bottleneck identification
        print(f"\nBOTTLENECK IDENTIFICATION:")
        print("-" * 40)
        self._print_bottlenecks(simplified, modular)
        
        # Recommendations
        print(f"\nRECOMMENDATIONS:")
        print("-" * 40)
        self._generate_recommendations(simplified, modular)
    
    def _print_system_metrics(self, name: str, analysis: ComponentAnalysis) -> None:
        """Print metrics for a system."""
        print(f"{name} System:")
        print(f"  Files: {analysis.file_count}")
        print(f"  Lines of Code: {analysis.line_count}")
        print(f"  Classes: {analysis.class_count}")
        print(f"  Methods: {analysis.method_count}")
        print(f"  Signals: {analysis.signal_count}")
        print(f"  Timers: {analysis.timer_count}")
        print(f"  Widgets: {analysis.widget_count}")
        print(f"  Dependencies: {analysis.dependency_count}")
        print(f"  Complexity Score: {analysis.complexity_score:.1f}")
    
    def _analyze_performance_implications(self, simplified: ComponentAnalysis, modular: ComponentAnalysis) -> None:
        """Analyze performance implications between systems."""
        print("Initialization Overhead:")
        if modular.file_count > simplified.file_count * 2:
            print(f"  → Modular system has {modular.file_count} files vs {simplified.file_count}")
            print(f"    Higher initialization overhead due to multi-file imports")
        else:
            print(f"  → Similar file counts, comparable initialization overhead")
        
        print(f"\nSignal Routing Efficiency:")
        if modular.signal_count > simplified.signal_count * 1.5:
            print(f"  → Modular system has {modular.signal_count} signals vs {simplified.signal_count}")
            print(f"    More complex signal routing, potential performance impact")
        elif simplified.signal_count > modular.signal_count * 1.5:
            print(f"  → Simplified system has {simplified.signal_count} signals vs {modular.signal_count}")
            print(f"    May have more direct but tightly coupled signal connections")
        else:
            print(f"  → Similar signal counts ({simplified.signal_count} vs {modular.signal_count})")
        
        print(f"\nRuntime Performance:")
        if simplified.complexity_score > modular.complexity_score * 1.3:
            print(f"  → Simplified system higher complexity ({simplified.complexity_score:.1f} vs {modular.complexity_score:.1f})")
            print(f"    Monolithic design may have performance bottlenecks")
        elif modular.complexity_score > simplified.complexity_score * 1.3:
            print(f"  → Modular system higher complexity ({modular.complexity_score:.1f} vs {simplified.complexity_score:.1f})")
            print(f"    Component overhead may impact performance")
        else:
            print(f"  → Similar complexity levels, comparable runtime performance expected")
    
    def _analyze_resource_usage(self, simplified: ComponentAnalysis, modular: ComponentAnalysis) -> None:
        """Analyze resource usage patterns."""
        print("Memory Allocation:")
        total_simplified = simplified.class_count + simplified.widget_count
        total_modular = modular.class_count + modular.widget_count
        
        print(f"  Simplified: {total_simplified} total objects (classes + widgets)")
        print(f"  Modular: {total_modular} total objects (classes + widgets)")
        
        if total_modular > total_simplified * 1.5:
            print(f"  → Modular system uses ~{(total_modular/total_simplified):.1f}x more objects")
            print(f"    Higher base memory usage but better encapsulation")
        else:
            print(f"  → Similar memory footprint expected")
        
        print(f"\nEvent Loop Impact:")
        if modular.timer_count > simplified.timer_count * 2:
            print(f"  → Modular system has {modular.timer_count} timers vs {simplified.timer_count}")
            print(f"    Higher event loop overhead")
        else:
            print(f"  → Reasonable timer usage in both systems")
    
    def _analyze_scalability(self, simplified: ComponentAnalysis, modular: ComponentAnalysis) -> None:
        """Analyze scalability characteristics."""
        print("Large ROM Handling:")
        for name, analysis in [("Simplified", simplified), ("Modular", modular)]:
            if 'large_roms' in analysis.scaling_factors:
                print(f"  {name}: {analysis.scaling_factors['large_roms']}")
        
        print(f"\nPreview Update Performance:")
        for name, analysis in [("Simplified", simplified), ("Modular", modular)]:
            if 'preview_updates' in analysis.scaling_factors:
                print(f"  {name}: {analysis.scaling_factors['preview_updates']}")
        
        print(f"\nFeature Addition Scalability:")
        for name, analysis in [("Simplified", simplified), ("Modular", modular)]:
            if 'modularity' in analysis.scaling_factors:
                print(f"  {name}: {analysis.scaling_factors['modularity']}")
    
    def _print_bottlenecks(self, simplified: ComponentAnalysis, modular: ComponentAnalysis) -> None:
        """Print identified bottlenecks."""
        print("Simplified System Bottlenecks:")
        for bottleneck in simplified.bottlenecks:
            print(f"  • {bottleneck}")
        
        print(f"\nModular System Bottlenecks:")
        for bottleneck in modular.bottlenecks:
            print(f"  • {bottleneck}")
    
    def _generate_recommendations(self, simplified: ComponentAnalysis, modular: ComponentAnalysis) -> None:
        """Generate optimization recommendations."""
        print("Performance Optimization Recommendations:")
        
        # Based on complexity scores
        if simplified.complexity_score > modular.complexity_score * 1.2:
            print("  • Consider adopting modular approach for simplified system")
            print("  • Break down large classes into smaller components")
        elif modular.complexity_score > simplified.complexity_score * 1.2:
            print("  • Optimize component initialization in modular system")
            print("  • Consider lazy loading for non-critical components")
        
        # Signal optimization
        high_signal_system = simplified if simplified.signal_count > modular.signal_count else modular
        if high_signal_system.signal_count > 15:
            print(f"  • Optimize signal routing in {high_signal_system.name}")
            print("  • Consider signal batching for high-frequency operations")
        
        # Timer optimization
        for name, analysis in [("Simplified", simplified), ("Modular", modular)]:
            if analysis.timer_count > 3:
                print(f"  • Consider timer consolidation in {name} system")
        
        # Memory optimization
        high_widget_system = simplified if simplified.widget_count > modular.widget_count else modular
        if high_widget_system.widget_count > 20:
            print(f"  • Consider widget pooling in {high_widget_system.name}")
            print("  • Implement lazy widget creation where possible")
        
        print(f"\nGeneral Recommendations:")
        print("  • Implement preview caching to reduce update overhead")
        print("  • Use debounced updates for high-frequency operations")
        print("  • Profile actual runtime performance under realistic loads")
        print("  • Monitor memory usage during extended operation")


def main():
    """Main analysis function."""
    base_path = os.path.dirname(os.path.abspath(__file__))
    analyzer = ArchitectureAnalyzer(base_path)
    analyzer.generate_performance_report()


if __name__ == "__main__":
    main()