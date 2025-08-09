"""
Test runner for sprite display fix comprehensive test suite

This script runs all tests related to the sprite display fix implementation,
providing organized output and summary statistics.

Usage:
    python tests/run_sprite_display_tests.py [options]
    
Options:
    --fast          Skip performance tests (faster execution)
    --integration   Run only integration tests
    --unit          Run only unit tests
    --performance   Run only performance tests  
    --regression    Run only regression tests
    --coverage      Generate coverage report
    --verbose       Verbose output
    --parallel      Run tests in parallel (if pytest-xdist available)
"""

import argparse
import subprocess
import sys
from pathlib import Path
import time


class SpriteDisplayTestRunner:
    """Comprehensive test runner for sprite display fix"""
    
    def __init__(self):
        self.test_files = {
            'unit': [
                'test_async_rom_cache.py',
                'test_preview_orchestrator.py', 
                'test_smart_preview_coordinator.py',
                'test_sprite_display_fix.py'
            ],
            'integration': [
                'test_manual_offset_integration.py',
            ],
            'performance': [
                'test_performance_benchmarks.py'
            ],
            'regression': [
                'test_sprite_display_regression.py'
            ]
        }
        
        self.test_dir = Path(__file__).parent
        self.results = {}
    
    def run_test_category(self, category: str, args: argparse.Namespace) -> dict:
        """Run tests for a specific category"""
        if category not in self.test_files:
            raise ValueError(f"Unknown test category: {category}")
        
        print(f"\n{'='*60}")
        print(f"Running {category.upper()} tests for sprite display fix")
        print(f"{'='*60}")
        
        test_files = self.test_files[category]
        category_results = {
            'passed': 0,
            'failed': 0,
            'skipped': 0,
            'errors': [],
            'duration': 0
        }
        
        for test_file in test_files:
            test_path = self.test_dir / test_file
            if not test_path.exists():
                print(f"⚠️  Test file not found: {test_file}")
                continue
            
            print(f"\n📋 Running {test_file}...")
            start_time = time.time()
            
            # Build pytest command
            cmd = ['python', '-m', 'pytest', str(test_path)]
            
            # Add common options
            if args.verbose:
                cmd.append('-v')
            else:
                cmd.append('-q')
            
            # Add category-specific options
            if category == 'performance':
                cmd.extend(['-m', 'performance'])
                if args.fast:
                    cmd.extend(['--maxfail=3'])  # Stop early on performance issues
            elif category == 'unit':
                cmd.extend(['-m', 'not performance'])
            
            # Add coverage if requested
            if args.coverage:
                cmd.extend([
                    '--cov=core',
                    '--cov=ui',
                    '--cov-report=term-missing',
                    '--cov-append'
                ])
            
            # Add parallel execution if requested
            if args.parallel:
                try:
                    import xdist
                    cmd.extend(['-n', 'auto'])
                except ImportError:
                    print("⚠️  pytest-xdist not installed, running sequentially")
            
            # Run the test
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300 if category != 'performance' else 600  # Longer timeout for performance tests
                )
                
                duration = time.time() - start_time
                category_results['duration'] += duration
                
                # Parse results
                if result.returncode == 0:
                    print(f"✅ {test_file} passed ({duration:.1f}s)")
                    category_results['passed'] += 1
                else:
                    print(f"❌ {test_file} failed ({duration:.1f}s)")
                    category_results['failed'] += 1
                    category_results['errors'].append({
                        'file': test_file,
                        'stdout': result.stdout,
                        'stderr': result.stderr
                    })
                
                # Show summary if verbose
                if args.verbose:
                    output_lines = result.stdout.split('\n')
                    for line in output_lines[-5:]:  # Last 5 lines usually have summary
                        if any(keyword in line.lower() for keyword in ['passed', 'failed', 'error', 'skipped']):
                            print(f"  {line}")
                
            except subprocess.TimeoutExpired:
                print(f"⏰ {test_file} timed out")
                category_results['failed'] += 1
                category_results['errors'].append({
                    'file': test_file,
                    'error': 'Test timed out'
                })
            except Exception as e:
                print(f"💥 {test_file} crashed: {e}")
                category_results['failed'] += 1
                category_results['errors'].append({
                    'file': test_file,
                    'error': str(e)
                })
        
        return category_results
    
    def run_all_tests(self, args: argparse.Namespace):
        """Run all test categories"""
        categories_to_run = []
        
        # Determine which categories to run
        if args.unit:
            categories_to_run.append('unit')
        elif args.integration:
            categories_to_run.append('integration')
        elif args.performance:
            categories_to_run.append('performance')
        elif args.regression:
            categories_to_run.append('regression')
        else:
            # Run all categories
            categories_to_run = ['unit', 'integration', 'regression']
            if not args.fast:
                categories_to_run.append('performance')
        
        print(f"🚀 Starting sprite display fix test suite")
        print(f"📁 Test directory: {self.test_dir}")
        print(f"🎯 Categories: {', '.join(categories_to_run)}")
        
        overall_start = time.time()
        
        # Run each category
        for category in categories_to_run:
            self.results[category] = self.run_test_category(category, args)
        
        overall_duration = time.time() - overall_start
        
        # Print summary
        self.print_summary(overall_duration)
    
    def print_summary(self, overall_duration: float):
        """Print comprehensive test summary"""
        print(f"\n{'='*60}")
        print(f"🏁 SPRITE DISPLAY FIX TEST RESULTS SUMMARY")
        print(f"{'='*60}")
        
        total_passed = sum(r['passed'] for r in self.results.values())
        total_failed = sum(r['failed'] for r in self.results.values())
        total_tests = total_passed + total_failed
        
        print(f"📊 Overall Results:")
        print(f"   ✅ Passed: {total_passed}")
        print(f"   ❌ Failed: {total_failed}")
        print(f"   📈 Success Rate: {(total_passed/total_tests*100):.1f}%" if total_tests > 0 else "   📈 Success Rate: N/A")
        print(f"   ⏱️  Total Duration: {overall_duration:.1f}s")
        
        # Category breakdown
        print(f"\n📋 Results by Category:")
        for category, results in self.results.items():
            category_total = results['passed'] + results['failed']
            success_rate = (results['passed']/category_total*100) if category_total > 0 else 0
            
            status_icon = "✅" if results['failed'] == 0 else "❌" if results['passed'] == 0 else "⚠️"
            
            print(f"   {status_icon} {category.upper()}: "
                  f"{results['passed']}/{category_total} passed "
                  f"({success_rate:.1f}%) in {results['duration']:.1f}s")
        
        # Error details
        if total_failed > 0:
            print(f"\n🚨 Error Details:")
            for category, results in self.results.items():
                if results['errors']:
                    print(f"\n   {category.upper()} Errors:")
                    for error in results['errors']:
                        print(f"     ❌ {error['file']}")
                        if 'error' in error:
                            print(f"        {error['error']}")
                        elif error.get('stderr'):
                            # Show first few lines of stderr
                            stderr_lines = error['stderr'].split('\n')[:3]
                            for line in stderr_lines:
                                if line.strip():
                                    print(f"        {line.strip()}")
        
        # Test coverage suggestions
        print(f"\n💡 Test Coverage Summary:")
        print(f"   🧪 Unit Tests: Core component functionality")
        print(f"   🔗 Integration: End-to-end signal chains") 
        print(f"   📈 Performance: Caching and response times")
        print(f"   🔒 Regression: Existing functionality preserved")
        
        # Recommendations
        if total_failed == 0:
            print(f"\n🎉 All tests passed! The sprite display fix is working correctly.")
        elif total_failed <= 2:
            print(f"\n⚠️  Minor issues detected. Review failed tests above.")
        else:
            print(f"\n🚨 Significant issues detected. Fix failing tests before deployment.")
        
        return total_failed == 0


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Run comprehensive tests for sprite display fix",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--fast', 
        action='store_true',
        help='Skip performance tests for faster execution'
    )
    
    parser.add_argument(
        '--unit', 
        action='store_true',
        help='Run only unit tests'
    )
    
    parser.add_argument(
        '--integration',
        action='store_true', 
        help='Run only integration tests'
    )
    
    parser.add_argument(
        '--performance',
        action='store_true',
        help='Run only performance tests'
    )
    
    parser.add_argument(
        '--regression',
        action='store_true',
        help='Run only regression tests'
    )
    
    parser.add_argument(
        '--coverage',
        action='store_true',
        help='Generate coverage report'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )
    
    parser.add_argument(
        '--parallel',
        action='store_true',
        help='Run tests in parallel (requires pytest-xdist)'
    )
    
    args = parser.parse_args()
    
    # Validate environment
    try:
        import pytest
    except ImportError:
        print("❌ pytest not found. Please install: pip install pytest pytest-qt")
        sys.exit(1)
    
    # Run tests
    runner = SpriteDisplayTestRunner()
    success = runner.run_all_tests(args)
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()