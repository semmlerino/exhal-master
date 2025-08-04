#!/usr/bin/env python3
"""
Static Analysis of Manual Offset Dialog Preview Bottlenecks

This script analyzes the source code to identify performance bottlenecks
in the preview update mechanism without requiring runtime execution.
"""

import ast
import re
from pathlib import Path
from typing import Any


def analyze_method_complexity(source_code: str, method_name: str) -> dict[str, Any]:
    """Analyze the complexity of a specific method."""

    class MethodAnalyzer(ast.NodeVisitor):
        def __init__(self):
            self.in_target_method = False
            self.method_stats = {
                "lines": 0,
                "function_calls": 0,
                "loops": 0,
                "conditionals": 0,
                "blocking_operations": [],
                "synchronous_calls": [],
                "qt_signal_emissions": [],
                "worker_creations": [],
                "timer_operations": []
            }

        def visit_FunctionDef(self, node):  # noqa: N802
            """Visit function definition nodes - AST visitor pattern requires this exact name."""
            if node.name == method_name:
                self.in_target_method = True
                self.method_stats["lines"] = len(node.body)
                self.generic_visit(node)
                self.in_target_method = False
            else:
                self.generic_visit(node)

        def visit_Call(self, node):  # noqa: N802
            """Visit call nodes - AST visitor pattern requires this exact name."""
            if self.in_target_method:
                self.method_stats["function_calls"] += 1

                # Identify potentially blocking operations
                if isinstance(node.func, ast.Attribute):
                    attr_name = node.func.attr

                    # Qt signal emissions
                    if attr_name == "emit":
                        self.method_stats["qt_signal_emissions"].append(attr_name)

                    # Worker thread operations
                    elif "Worker" in str(node.func) or attr_name in ["start", "wait", "join"]:
                        self.method_stats["worker_creations"].append(attr_name)

                    # Timer operations
                    elif attr_name in ["start", "stop", "timeout"]:
                        self.method_stats["timer_operations"].append(attr_name)

                    # Potentially blocking operations
                    elif attr_name in ["read", "write", "load", "save", "compress", "decompress"]:
                        self.method_stats["blocking_operations"].append(attr_name)

                    # Synchronous processing
                    elif attr_name in ["processEvents", "exec", "wait"]:
                        self.method_stats["synchronous_calls"].append(attr_name)

                elif isinstance(node.func, ast.Name):
                    func_name = node.func.id

                    # File operations
                    if func_name in ["open", "read", "write"]:
                        self.method_stats["blocking_operations"].append(func_name)

            self.generic_visit(node)

        def visit_For(self, node):  # noqa: N802
            """Visit for loop nodes - AST visitor pattern requires this exact name."""
            if self.in_target_method:
                self.method_stats["loops"] += 1
            self.generic_visit(node)

        def visit_While(self, node):  # noqa: N802
            """Visit while loop nodes - AST visitor pattern requires this exact name."""
            if self.in_target_method:
                self.method_stats["loops"] += 1
            self.generic_visit(node)

        def visit_If(self, node):  # noqa: N802
            """Visit if statement nodes - AST visitor pattern requires this exact name."""
            if self.in_target_method:
                self.method_stats["conditionals"] += 1
            self.generic_visit(node)

    try:
        tree = ast.parse(source_code)
        analyzer = MethodAnalyzer()
        analyzer.visit(tree)
    except SyntaxError as e:
        return {"error": f"Syntax error: {e}"}
    else:
        return analyzer.method_stats


def analyze_timing_patterns(source_code: str) -> dict[str, Any]:
    """Analyze timing-related patterns in the code."""

    patterns = {
        "debounce_timers": [],
        "delays": [],
        "timeouts": [],
        "frame_rates": [],
        "intervals": []
    }

    # Find timer configurations
    timer_pattern = r"(\w+)\.start\((\d+)\)"
    for match in re.finditer(timer_pattern, source_code):
        timer_name, delay = match.groups()
        patterns["delays"].append({"timer": timer_name, "delay_ms": int(delay)})

    # Find timeout values
    timeout_pattern = r"timeout\s*=\s*(\d+)"
    for match in re.finditer(timeout_pattern, source_code):
        timeout_ms = int(match.group(1))
        patterns["timeouts"].append(timeout_ms)

    # Find debounce patterns
    debounce_pattern = r"debounce.*?(\d+)"
    for match in re.finditer(debounce_pattern, source_code, re.IGNORECASE):
        delay_ms = int(match.group(1))
        patterns["debounce_timers"].append(delay_ms)

    # Find frame rate references
    fps_pattern = r"(\d+)\s*fps|(\d+).*?frame"
    for match in re.finditer(fps_pattern, source_code, re.IGNORECASE):
        fps = int(match.group(1) or match.group(2))
        patterns["frame_rates"].append(fps)

    return patterns


def analyze_worker_usage(source_code: str) -> dict[str, Any]:
    """Analyze worker thread usage patterns."""

    patterns = {
        "worker_classes": [],
        "cleanup_calls": [],
        "creation_patterns": [],
        "lifecycle_issues": []
    }

    # Find worker class definitions
    worker_pattern = r"class\s+(\w*Worker\w*)"
    for match in re.finditer(worker_pattern, source_code):
        patterns["worker_classes"].append(match.group(1))

    # Find cleanup operations
    cleanup_pattern = r"cleanup_worker|WorkerManager\.cleanup"
    patterns["cleanup_calls"] = len(re.findall(cleanup_pattern, source_code))

    # Find worker creation patterns
    creation_pattern = r"(\w*Worker\w*)\("
    for match in re.finditer(creation_pattern, source_code):
        worker_class = match.group(1)
        if "Worker" in worker_class:
            patterns["creation_patterns"].append(worker_class)

    # Identify potential lifecycle issues
    if len(patterns["creation_patterns"]) > patterns["cleanup_calls"] * 2:
        patterns["lifecycle_issues"].append("Potential worker cleanup mismatch")

    return patterns


def analyze_memory_patterns(source_code: str) -> dict[str, Any]:
    """Analyze memory usage patterns."""

    patterns = {
        "large_allocations": [],
        "cache_references": [],
        "weak_references": [],
        "potential_leaks": []
    }

    # Find cache usage
    cache_pattern = r"cache|Cache"
    patterns["cache_references"] = len(re.findall(cache_pattern, source_code))

    # Find weak references
    weak_ref_pattern = r"weakref"
    patterns["weak_references"] = len(re.findall(weak_ref_pattern, source_code))

    # Find large data structures
    large_data_pattern = r"(\d+)\s*\*\s*(\d+)|bytes\((\d+)\)"
    for match in re.finditer(large_data_pattern, source_code):
        if match.group(1) and match.group(2):
            size = int(match.group(1)) * int(match.group(2))
        elif match.group(3):
            size = int(match.group(3))
        else:
            continue

        if size > 10000:  # > 10KB
            patterns["large_allocations"].append(size)

    return patterns


def calculate_performance_score(analysis_results: dict[str, Any]) -> dict[str, Any]:
    """Calculate performance scores based on analysis results."""

    scores = {
        "responsiveness": 100,  # Start with perfect score
        "memory_efficiency": 100,
        "thread_safety": 100,
        "overall": 100
    }

    issues = []

    # Analyze method complexity
    if "method_analysis" in analysis_results:
        method_stats = analysis_results["method_analysis"]

        # Penalize for high complexity
        if method_stats.get("function_calls", 0) > 20:
            scores["responsiveness"] -= 20
            issues.append("High method complexity (many function calls)")

        # Penalize for blocking operations
        blocking_ops = len(method_stats.get("blocking_operations", []))
        if blocking_ops > 0:
            scores["responsiveness"] -= blocking_ops * 10
            issues.append(f"{blocking_ops} potentially blocking operations")

        # Penalize for synchronous calls
        sync_calls = len(method_stats.get("synchronous_calls", []))
        if sync_calls > 0:
            scores["thread_safety"] -= sync_calls * 15
            issues.append(f"{sync_calls} synchronous calls detected")

    # Analyze timing patterns
    if "timing_analysis" in analysis_results:
        timing = analysis_results["timing_analysis"]

        # Check debounce timing
        debounce_delays = timing.get("debounce_timers", [])
        if any(delay > 50 for delay in debounce_delays):
            scores["responsiveness"] -= 25
            issues.append("High debounce delays (>50ms) detected")

        # Check cleanup timeouts
        timeouts = timing.get("timeouts", [])
        if any(timeout > 2000 for timeout in timeouts):
            scores["responsiveness"] -= 15
            issues.append("Long cleanup timeouts (>2s) detected")

    # Analyze worker usage
    if "worker_analysis" in analysis_results:
        worker = analysis_results["worker_analysis"]

        if worker.get("lifecycle_issues"):
            scores["memory_efficiency"] -= 30
            scores["thread_safety"] -= 20
            issues.append("Worker lifecycle management issues")

        # Penalize for excessive worker creation
        creation_count = len(worker.get("creation_patterns", []))
        if creation_count > 5:
            scores["responsiveness"] -= 10
            issues.append("Excessive worker thread creation")

    # Analyze memory patterns
    if "memory_analysis" in analysis_results:
        memory = analysis_results["memory_analysis"]

        # Reward cache usage
        if memory.get("cache_references", 0) > 0:
            scores["memory_efficiency"] += 5
        else:
            scores["memory_efficiency"] -= 20
            issues.append("No caching mechanisms detected")

        # Reward weak references
        if memory.get("weak_references", 0) > 0:
            scores["memory_efficiency"] += 10

        # Penalize large allocations
        large_allocs = len(memory.get("large_allocations", []))
        if large_allocs > 2:
            scores["memory_efficiency"] -= large_allocs * 5
            issues.append(f"{large_allocs} large memory allocations")

    # Calculate overall score
    scores["overall"] = (
        scores["responsiveness"] * 0.4 +
        scores["memory_efficiency"] * 0.3 +
        scores["thread_safety"] * 0.3
    )

    # Ensure scores don't go below 0
    for key in scores:
        scores[key] = max(0, scores[key])

    return {
        "scores": scores,
        "issues": issues,
        "grade": _get_performance_grade(scores["overall"])
    }


def _get_performance_grade(score: float) -> str:
    """Convert numeric score to letter grade."""
    if score >= 90:
        return "A (Excellent)"
    if score >= 80:
        return "B (Good)"
    if score >= 70:
        return "C (Fair)"
    if score >= 60:
        return "D (Poor)"
    return "F (Critical Issues)"


def analyze_optimization_potential(source_code: str) -> dict[str, Any]:
    """Analyze potential optimizations based on code patterns."""

    optimizations = {
        "caching_opportunities": [],
        "debouncing_improvements": [],
        "worker_pool_benefits": [],
        "memory_optimizations": [],
        "ui_responsiveness": []
    }

    # Caching opportunities
    if "cache" not in source_code.lower():
        optimizations["caching_opportunities"].append(
            "Implement preview result caching with LRU eviction"
        )

    # Debouncing improvements
    if "100" in source_code and "debounce" in source_code.lower():
        optimizations["debouncing_improvements"].append(
            "Reduce debounce delay from 100ms to 16ms for 60 FPS responsiveness"
        )

    # Worker pool benefits
    if "Worker(" in source_code and "pool" not in source_code.lower():
        optimizations["worker_pool_benefits"].append(
            "Implement worker thread pool to reduce creation overhead"
        )

    # Memory optimizations
    if "weakref" not in source_code:
        optimizations["memory_optimizations"].append(
            "Use weak references to prevent circular references"
        )

    # UI responsiveness
    if "processEvents" in source_code:
        optimizations["ui_responsiveness"].append(
            "Avoid processEvents() calls - use proper async patterns instead"
        )

    return optimizations


def main():
    """Run comprehensive static analysis of preview bottlenecks."""

    print("Manual Offset Dialog Preview Performance Analysis")
    print("=" * 55)
    print()

    # Load source files
    project_root = Path(__file__).parent

    files_to_analyze = [
        "ui/dialogs/manual_offset_unified_integrated.py",
        "ui/common/smart_preview_coordinator.py",
        "ui/rom_extraction/workers/preview_worker.py",
        "ui/common/worker_manager.py"
    ]

    all_source_code = ""
    file_analyses = {}

    for file_path in files_to_analyze:
        full_path = project_root / file_path
        if full_path.exists():
            print(f"Analyzing {file_path}...")

            with open(full_path, encoding="utf-8") as f:
                source_code = f.read()
                all_source_code += source_code + "\n"

            # Analyze this specific file
            file_analyses[file_path] = {
                "timing_analysis": analyze_timing_patterns(source_code),
                "worker_analysis": analyze_worker_usage(source_code),
                "memory_analysis": analyze_memory_patterns(source_code)
            }
        else:
            print(f"Warning: {file_path} not found")

    # Analyze key methods
    print("\nAnalyzing critical methods...")

    method_analyses = {}
    critical_methods = [
        "_update_preview",
        "_handle_drag_preview",
        "_handle_release_preview",
        "request_preview",
        "_cleanup_workers"
    ]

    for method_name in critical_methods:
        print(f"  Analyzing {method_name}()...")
        analysis = analyze_method_complexity(all_source_code, method_name)
        method_analyses[method_name] = analysis

    # Comprehensive analysis
    print("\nPerforming comprehensive analysis...")

    overall_analysis = {
        "method_analysis": method_analyses,
        "timing_analysis": analyze_timing_patterns(all_source_code),
        "worker_analysis": analyze_worker_usage(all_source_code),
        "memory_analysis": analyze_memory_patterns(all_source_code)
    }

    # Calculate performance scores
    performance_assessment = calculate_performance_score(overall_analysis)

    # Identify optimization opportunities
    optimizations = analyze_optimization_potential(all_source_code)

    # Generate report
    print("\n" + "=" * 60)
    print("PERFORMANCE ANALYSIS RESULTS")
    print("=" * 60)

    # Performance Scores
    scores = performance_assessment["scores"]
    print("\nPERFORMANCE SCORES:")
    print(f"  Responsiveness:     {scores['responsiveness']:.1f}/100")
    print(f"  Memory Efficiency:  {scores['memory_efficiency']:.1f}/100")
    print(f"  Thread Safety:      {scores['thread_safety']:.1f}/100")
    print(f"  Overall Grade:      {performance_assessment['grade']} ({scores['overall']:.1f}/100)")

    # Critical Issues
    if performance_assessment["issues"]:
        print("\nCRITICAL ISSUES IDENTIFIED:")
        for issue in performance_assessment["issues"]:
            print(f"  ⚠️  {issue}")

    # Method Complexity Analysis
    print("\nMETHOD COMPLEXITY ANALYSIS:")
    for method_name, analysis in method_analyses.items():
        if "error" not in analysis:
            blocking_count = len(analysis.get("blocking_operations", []))
            sync_count = len(analysis.get("synchronous_calls", []))

            complexity_score = "LOW"
            if analysis.get("function_calls", 0) > 15 or blocking_count > 0 or sync_count > 0:
                complexity_score = "HIGH"
            elif analysis.get("function_calls", 0) > 8:
                complexity_score = "MEDIUM"

            print(f"  {method_name}():")
            print(f"    Complexity: {complexity_score}")
            print(f"    Function calls: {analysis.get('function_calls', 0)}")
            print(f"    Blocking operations: {blocking_count}")
            print(f"    Synchronous calls: {sync_count}")

    # Timing Analysis
    timing = overall_analysis["timing_analysis"]
    print("\nTIMING CONFIGURATION ANALYSIS:")
    print(f"  Debounce delays found: {timing.get('debounce_timers', [])}")
    print(f"  Timeout values: {timing.get('timeouts', [])}")
    print(f"  Timer delays: {[d['delay_ms'] for d in timing.get('delays', [])]}")

    # Worker Analysis
    worker = overall_analysis["worker_analysis"]
    print("\nWORKER THREAD ANALYSIS:")
    print(f"  Worker classes: {len(worker.get('worker_classes', []))}")
    print(f"  Cleanup calls: {worker.get('cleanup_calls', 0)}")
    print(f"  Creation patterns: {len(worker.get('creation_patterns', []))}")
    if worker.get("lifecycle_issues"):
        print(f"  ⚠️  Issues: {worker['lifecycle_issues']}")

    # Memory Analysis
    memory = overall_analysis["memory_analysis"]
    print("\nMEMORY USAGE ANALYSIS:")
    print(f"  Cache references: {memory.get('cache_references', 0)}")
    print(f"  Weak references: {memory.get('weak_references', 0)}")
    print(f"  Large allocations: {len(memory.get('large_allocations', []))}")

    # Optimization Recommendations
    print("\nOPTIMIZATION RECOMMENDATIONS:")

    for category, recommendations in optimizations.items():
        if recommendations:
            print(f"  {category.replace('_', ' ').title()}:")
            for rec in recommendations:
                print(f"    • {rec}")

    # Specific Bottleneck Analysis
    print("\nBOTTLENECK ANALYSIS:")

    bottlenecks = []

    # Check _update_preview method
    if "_update_preview" in method_analyses:
        update_analysis = method_analyses["_update_preview"]
        if update_analysis.get("blocking_operations"):
            bottlenecks.append("_update_preview() contains blocking operations")
        if update_analysis.get("function_calls", 0) > 10:
            bottlenecks.append("_update_preview() has high function call overhead")

    # Check debounce timing
    if any(delay > 50 for delay in timing.get("debounce_timers", [])):
        bottlenecks.append("Debounce delays exceed responsive threshold (>50ms)")

    # Check worker creation
    creation_count = len(worker.get("creation_patterns", []))
    cleanup_count = worker.get("cleanup_calls", 0)
    if creation_count > cleanup_count * 2:
        bottlenecks.append("Worker thread creation/cleanup imbalance detected")

    # Check caching
    if memory.get("cache_references", 0) == 0:
        bottlenecks.append("No preview caching detected - repeated work likely")

    if bottlenecks:
        print("  Primary bottlenecks identified:")
        for bottleneck in bottlenecks:
            print(f"    🔴 {bottleneck}")
    else:
        print("  ✅ No major bottlenecks detected in static analysis")

    # Final Assessment
    print("\nFINAL ASSESSMENT:")

    if scores["overall"] >= 80:
        print("  ✅ Performance appears acceptable based on static analysis")
    elif scores["overall"] >= 60:
        print("  ⚠️  Some performance concerns identified")
    else:
        print("  🔴 Significant performance issues likely present")

    print("\nRecommended next steps:")
    print("  1. Profile actual runtime performance with real data")
    print("  2. Implement caching if not present")
    print("  3. Reduce debounce delays for better responsiveness")
    print("  4. Consider worker thread pooling")
    print("  5. Measure memory usage during rapid operations")

    print("\nAnalysis complete! 🎯")


if __name__ == "__main__":
    main()
