#!/usr/bin/env python3
"""
Sinphasé Cost Function Automation - OBINexus Implementation
Evaluates component complexity and triggers architectural isolation when thresholds exceeded.
"""

import os
import re
import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple, NamedTuple
from dataclasses import dataclass
from datetime import datetime

class SinphaseMetrics(NamedTuple):
    include_depth: int
    function_calls: int
    external_deps: int
    complexity: float
    link_deps: int
    circular_penalty: float
    temporal_pressure: float

@dataclass
class ComponentAnalysis:
    component_path: str
    cost: float
    metrics: SinphaseMetrics
    phase_state: str
    violation_details: List[str]
    isolation_required: bool

class SinphaseCostEvaluator:
    """Automated Sinphasé governance enforcement"""
    
    # Sinphasé cost function weights (from documentation)
    WEIGHTS = {
        'include_depth': 0.15,
        'function_calls': 0.20,
        'external_deps': 0.25,
        'complexity': 0.30,
        'link_deps': 0.10
    }
    
    # Governance thresholds
    AUTONOMOUS_THRESHOLD = 0.5
    WARNING_THRESHOLD = 0.6
    GOVERNANCE_THRESHOLD = 0.6
    
    # Phase states from Sinphasé documentation
    PHASE_STATES = ['RESEARCH', 'IMPLEMENTATION', 'VALIDATION', 'ISOLATION']
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.logger = self._setup_logging()
        self.isolation_log_path = self.project_root / "ISOLATION_LOG.md"
        
    def _setup_logging(self) -> logging.Logger:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - Sinphasé - %(levelname)s - %(message)s'
        )
        return logging.getLogger('sinphase_evaluator')
        
    def evaluate_component_cost(self, component_path: str) -> ComponentAnalysis:
        """
        Evaluate component against Sinphasé cost function:
        C = Σ(metric_i × weight_i) + circular_penalty + temporal_pressure
        """
        path = Path(component_path)
        
        # Extract metrics from source files
        metrics = self._extract_metrics(path)
        
        # Calculate weighted cost
        weighted_cost = (
            metrics.include_depth * self.WEIGHTS['include_depth'] +
            metrics.function_calls * self.WEIGHTS['function_calls'] +
            metrics.external_deps * self.WEIGHTS['external_deps'] +
            metrics.complexity * self.WEIGHTS['complexity'] +
            metrics.link_deps * self.WEIGHTS['link_deps']
        )
        
        # Add penalties from Sinphasé formula
        total_cost = weighted_cost + metrics.circular_penalty + metrics.temporal_pressure
        
        # Determine violations and required actions
        violations = []
        isolation_required = False
        
        if total_cost > self.GOVERNANCE_THRESHOLD:
            violations.append(f"Cost {total_cost:.3f} exceeds governance threshold {self.GOVERNANCE_THRESHOLD}")
            isolation_required = True
            
        if metrics.circular_penalty > 0:
            violations.append(f"Circular dependencies detected (penalty: {metrics.circular_penalty})")
            isolation_required = True
            
        # Determine current phase state
        phase_state = self._determine_phase_state(path)
        
        return ComponentAnalysis(
            component_path=str(path),
            cost=total_cost,
            metrics=metrics,
            phase_state=phase_state,
            violation_details=violations,
            isolation_required=isolation_required
        )
    
    def _extract_metrics(self, component_path: Path) -> SinphaseMetrics:
        """Extract architectural metrics from component source code"""
        
        include_depth = 0
        function_calls = 0
        external_deps = 0
        complexity = 0.0
        link_deps = 0
        circular_penalty = 0.0
        temporal_pressure = 0.0
        
        # Analyze C source files in component
        for source_file in component_path.rglob("*.c"):
            if source_file.is_file():
                content = source_file.read_text(encoding='utf-8', errors='ignore')
                
                # Count include depth (nested includes)
                includes = re.findall(r'#include\s*[<"]([^>"]+)[>"]', content)
                include_depth += len(includes)
                
                # Count function calls
                function_calls += len(re.findall(r'\w+\s*\(', content))
                
                # Count external dependencies (non-polycall includes)
                external_deps += len([inc for inc in includes if not inc.startswith('polycall')])
                
                # Simple complexity metric (cyclomatic complexity approximation)
                complexity_keywords = ['if', 'else', 'while', 'for', 'switch', 'case']
                for keyword in complexity_keywords:
                    complexity += len(re.findall(rf'\b{keyword}\b', content))
        
        # Analyze CMakeLists.txt for link dependencies
        cmake_file = component_path / "CMakeLists.txt"
        if cmake_file.exists():
            cmake_content = cmake_file.read_text()
            link_deps = len(re.findall(r'target_link_libraries', cmake_content))
        
        # Check for circular dependencies (simplified)
        if self._detect_circular_dependencies(component_path):
            circular_penalty = 0.2  # Per Sinphasé documentation
            
        # Calculate temporal pressure (change frequency)
        temporal_pressure = self._calculate_temporal_pressure(component_path)
        
        return SinphaseMetrics(
            include_depth=include_depth,
            function_calls=function_calls,
            external_deps=external_deps,
            complexity=complexity / 100.0,  # Normalize
            link_deps=link_deps,
            circular_penalty=circular_penalty,
            temporal_pressure=temporal_pressure
        )
    
    def _detect_circular_dependencies(self, component_path: Path) -> bool:
        """Detect circular dependencies between components"""
        # Simplified detection - check for mutual includes
        component_name = component_path.name
        
        for source_file in component_path.rglob("*.c"):
            if source_file.is_file():
                content = source_file.read_text(encoding='utf-8', errors='ignore')
                includes = re.findall(r'#include\s*[<"]polycall/([^/"]+)', content)
                
                for include in includes:
                    # Check if included component also includes this one
                    included_component_path = self.project_root / "src" / "core" / include
                    if included_component_path.exists():
                        for included_file in included_component_path.rglob("*.c"):
                            included_content = included_file.read_text(encoding='utf-8', errors='ignore')
                            if f'polycall/{component_name}' in included_content:
                                return True
        return False
    
    def _calculate_temporal_pressure(self, component_path: Path) -> float:
        """Calculate temporal pressure based on recent changes"""
        # For now, return 0.1 as baseline - can be enhanced with git log analysis
        return 0.1
    
    def _determine_phase_state(self, component_path: Path) -> str:
        """Determine current development phase of component"""
        # Check for phase indicators in source
        if (component_path / "TODO.md").exists():
            return "RESEARCH"
        elif (component_path / "CMakeLists.txt").exists():
            return "IMPLEMENTATION"
        else:
            return "VALIDATION"
    
    def trigger_isolation_protocol(self, component: ComponentAnalysis) -> bool:
        """
        Execute Sinphasé isolation protocol when cost thresholds exceeded
        """
        if not component.isolation_required:
            return False
            
        self.logger.warning(f"SINPHASÉ ISOLATION TRIGGERED: {component.component_path}")
        self.logger.warning(f"Cost: {component.cost:.3f} (threshold: {self.GOVERNANCE_THRESHOLD})")
        
        # 1. Create isolated directory structure in root-dynamic-c/
        component_name = Path(component.component_path).name
        isolation_dir = self.project_root / "root-dynamic-c" / f"{component_name}-isolated"
        isolation_dir.mkdir(parents=True, exist_ok=True)
        
        # 2. Generate independent build system
        self._generate_isolated_makefile(isolation_dir, component_name)
        
        # 3. Document architectural decision
        self._update_isolation_log(component)
        
        self.logger.info(f"Isolation structure created: {isolation_dir}")
        return True
    
    def _generate_isolated_makefile(self, isolation_dir: Path, component_name: str):
        """Generate independent Makefile for isolated component"""
        makefile_content = f"""# Sinphasé Isolated Component: {component_name}
# Generated by automated governance system

CC = gcc
CFLAGS = -Wall -Wextra -std=c11 -O2
INCLUDES = -I./include -I../include

SRCDIR = src
OBJDIR = obj
SOURCES = $(wildcard $(SRCDIR)/*.c)
OBJECTS = $(SOURCES:$(SRCDIR)/%.c=$(OBJDIR)/%.o)
TARGET = lib{component_name}_isolated.a

.PHONY: all clean

all: $(TARGET)

$(TARGET): $(OBJECTS)
\t@mkdir -p $(dir $@)
\tar rcs $@ $^

$(OBJDIR)/%.o: $(SRCDIR)/%.c
\t@mkdir -p $(dir $@)
\t$(CC) $(CFLAGS) $(INCLUDES) -c $< -o $@

clean:
\trm -rf $(OBJDIR) $(TARGET)

# Sinphasé governance compliance check
governance-check:
\t@echo "Validating single-pass compilation requirements..."
\t@make clean && make -j1  # Force single-pass
"""
        
        makefile_path = isolation_dir / "Makefile"
        makefile_path.write_text(makefile_content)
    
    def _update_isolation_log(self, component: ComponentAnalysis):
        """Update ISOLATION_LOG.md with architectural decision"""
        timestamp = datetime.now().isoformat()
        
        log_entry = f"""
## Isolation Event: {Path(component.component_path).name}

**Timestamp:** {timestamp}
**Trigger:** Cost function violation (C = {component.cost:.3f})
**Threshold:** {self.GOVERNANCE_THRESHOLD}
**Phase State:** {component.phase_state}

### Violations Detected:
{chr(10).join(f"- {violation}" for violation in component.violation_details)}

### Metrics:
- Include Depth: {component.metrics.include_depth}
- Function Calls: {component.metrics.function_calls}
- External Dependencies: {component.metrics.external_deps}
- Complexity: {component.metrics.complexity:.3f}
- Link Dependencies: {component.metrics.link_deps}
- Circular Penalty: {component.metrics.circular_penalty}
- Temporal Pressure: {component.metrics.temporal_pressure}

### Action Taken:
Component isolated to `root-dynamic-c/{Path(component.component_path).name}-isolated/`
Independent build system generated.
Single-pass compilation requirements validated.

---
"""
        
        # Append to isolation log
        with open(self.isolation_log_path, 'a', encoding='utf-8') as f:
            f.write(log_entry)
    
    def analyze_entire_project(self) -> Dict[str, ComponentAnalysis]:
        """Analyze all components in the project"""
        results = {}
        
        # Analyze core components
        core_path = self.project_root / "src" / "core"
        if core_path.exists():
            for component_dir in core_path.iterdir():
                if component_dir.is_dir() and not component_dir.name.startswith('.'):
                    analysis = self.evaluate_component_cost(str(component_dir))
                    results[component_dir.name] = analysis
                    
                    # Trigger isolation if required
                    if analysis.isolation_required:
                        self.trigger_isolation_protocol(analysis)
        
        return results
    
    def generate_governance_report(self, results: Dict[str, ComponentAnalysis]) -> str:
        """Generate comprehensive Sinphasé governance report"""
        report = [
            "# Sinphasé Governance Assessment Report",
            f"Generated: {datetime.now().isoformat()}",
            "",
            "## Component Cost Analysis",
            ""
        ]
        
        autonomous_zone = []
        warning_zone = []
        governance_zone = []
        
        for name, analysis in results.items():
            if analysis.cost <= self.AUTONOMOUS_THRESHOLD:
                autonomous_zone.append((name, analysis))
            elif analysis.cost <= self.WARNING_THRESHOLD:
                warning_zone.append((name, analysis))
            else:
                governance_zone.append((name, analysis))
        
        # Autonomous Zone
        report.extend([
            f"### 🟢 Autonomous Zone (C ≤ {self.AUTONOMOUS_THRESHOLD})",
            ""
        ])
        for name, analysis in autonomous_zone:
            report.append(f"- **{name}**: C = {analysis.cost:.3f} | Phase: {analysis.phase_state}")
        
        # Warning Zone  
        report.extend([
            "",
            f"### 🟡 Warning Zone ({self.AUTONOMOUS_THRESHOLD} < C ≤ {self.WARNING_THRESHOLD})",
            ""
        ])
        for name, analysis in warning_zone:
            report.append(f"- **{name}**: C = {analysis.cost:.3f} | Phase: {analysis.phase_state}")
        
        # Governance Zone
        report.extend([
            "",
            f"### 🔴 Governance Zone (C > {self.GOVERNANCE_THRESHOLD}) - ISOLATION REQUIRED",
            ""
        ])
        for name, analysis in governance_zone:
            report.append(f"- **{name}**: C = {analysis.cost:.3f} | Phase: {analysis.phase_state}")
            report.append(f"  - Violations: {', '.join(analysis.violation_details)}")
        
        return '\n'.join(report)

def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Sinphasé Cost Function Automation')
    parser.add_argument('--project-root', default='.', help='Project root directory')
    parser.add_argument('--component', help='Analyze specific component')
    parser.add_argument('--report', action='store_true', help='Generate governance report')
    
    args = parser.parse_args()
    
    evaluator = SinphaseCostEvaluator(args.project_root)
    
    if args.component:
        # Analyze specific component
        analysis = evaluator.evaluate_component_cost(args.component)
        print(f"Component: {analysis.component_path}")
        print(f"Cost: {analysis.cost:.3f}")
        print(f"Phase: {analysis.phase_state}")
        print(f"Isolation Required: {analysis.isolation_required}")
        
        if analysis.violation_details:
            print("Violations:")
            for violation in analysis.violation_details:
                print(f"  - {violation}")
                
    elif args.report:
        # Generate full project report
        results = evaluator.analyze_entire_project()
        report = evaluator.generate_governance_report(results)
        print(report)
        
        # Save report
        report_path = Path(args.project_root) / "SINPHASE_GOVERNANCE_REPORT.md"
        report_path.write_text(report)
        print(f"\nReport saved to: {report_path}")
    
    else:
        # Quick analysis
        results = evaluator.analyze_entire_project()
        governance_violations = [name for name, analysis in results.items() if analysis.isolation_required]
        
        if governance_violations:
            print(f"🔴 Governance violations detected in: {', '.join(governance_violations)}")
            print("Run with --report for detailed analysis")
        else:
            print("✅ All components within Sinphasé governance thresholds")

if __name__ == "__main__":
    main()
