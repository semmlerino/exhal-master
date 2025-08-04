# Archived Documentation

This directory contains documentation and assets related to deprecated components that have been replaced with improved implementations.

## Archived Files

### `manual_offset_dialog_architecture_analysis.md`
- **Date Archived**: August 2, 2025
- **Purpose**: Analysis of the original ManualOffsetDialog architecture issues
- **Historical Value**: Documents the problems that led to the simplified implementation
- **Status**: Completed - issues resolved in ManualOffsetDialogSimplified

### `manual_offset.jpg`
- **Date**: August 2, 2025  
- **Purpose**: Screenshot used for UX analysis showing cramped dialog layout
- **Issues Captured**: Tiny preview (400x400), poor space allocation (55% controls vs 45% preview), hidden tabs
- **Resolution**: Fixed in ManualOffsetDialogSimplified with 70% preview space and larger default size (1400x900)

## Related Improvements

The analysis in these archived files led to the following implemented solutions:

### Architecture Simplification
- **From**: Over-engineered MVP pattern with 4 services  
- **To**: Direct business logic consolidation in dialog class
- **Result**: Eliminated Qt lifecycle bugs and "buggy and janky" behavior

### UX Improvements  
- **From**: 400x400 preview, poor space allocation
- **To**: 800x800 preview capability, 70/30 space split
- **Result**: Preview-focused interface optimized for sprite browsing

### Technical Stability
- **From**: Layout conflicts, position corruption, memory issues
- **To**: Comprehensive validation, proper size hints, debug logging
- **Result**: Enterprise-grade window stability

## Historical Context

These files document the journey from a problematic implementation to a robust, maintainable solution. They serve as valuable context for understanding design decisions in the current simplified implementation.

**Current Implementation**: `ManualOffsetDialogSimplified` - see main codebase for active development.