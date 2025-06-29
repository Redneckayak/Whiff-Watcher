# Whiff Watcher - MLB Strikeout Analytics

## Overview

Whiff Watcher is a Flask-based web application that generates MLB strikeout analytics by combining batter and pitcher strikeout rates. The application fetches real-time MLB data and calculates "whiff ratings" for games, providing insights into potential strikeout scenarios.

## System Architecture

### Frontend Architecture
- **Framework**: HTML/CSS/JavaScript with Bootstrap 5.1.3 for responsive design
- **UI Components**: Single-page dashboard with data tables and interactive controls
- **Styling**: Custom CSS with Font Awesome icons for enhanced visual appeal
- **Data Visualization**: Bootstrap-styled tables for displaying whiff ratings and statistics

### Backend Architecture
- **Framework**: Flask (Python web framework)
- **Architecture Pattern**: Simple REST API with template rendering
- **Data Processing**: Custom WhiffWatcher class for MLB data analysis
- **API Design**: RESTful endpoints for data retrieval and file generation

### Data Storage Solutions
- **Primary Storage**: JSON files for data persistence and external integration
- **File System**: Static file serving for generated JSON data
- **Cache Strategy**: In-memory processing with file-based output

## Key Components

### Core Application (app.py)
- **Purpose**: Main Flask application with API endpoints
- **Key Routes**:
  - `/` - Dashboard rendering
  - `/api/whiff-watch-data` - Real-time data API
  - `/api/generate-json` - JSON file generation for external systems
- **Error Handling**: Comprehensive exception handling with JSON error responses

### Data Processing Engine (whiff_watcher.py)
- **Purpose**: MLB data fetching and whiff rating calculations
- **Key Features**:
  - Integration with MLB-StatsAPI
  - Minimum at-bat filtering (150 AB requirement)
  - Strikeout rate calculations for batters and pitchers
- **Season Configuration**: Configurable for current season (2025)

### Frontend Interface (templates/index.html)
- **Purpose**: User dashboard for data visualization and interaction
- **Features**:
  - Real-time data loading
  - JSON file generation controls
  - Responsive design with Bootstrap grid system

## Data Flow

1. **Data Ingestion**: WhiffWatcher fetches authentic 2025 MLB data via MLB StatsAPI
2. **Data Processing**: 
   - Retrieves real statistics from teams playing today's games
   - Gets actual probable pitchers with current season strikeout rates
   - Filters batters with minimum at-bat thresholds (50+ for current players)
   - Creates accurate game matchups from today's scheduled games
3. **API Response**: Processed authentic data served via REST API endpoints
4. **File Generation**: JSON data with real statistics exported for Bubble integration
5. **Frontend Display**: Dashboard renders current MLB data in interactive tables

## External Dependencies

### MLB Data Integration
- **Service**: MLB-StatsAPI for real-time baseball statistics
- **Data Types**: Player stats, team rosters, probable pitchers
- **Update Frequency**: Real-time during baseball season

### Third-Party Libraries
- **Flask**: Web framework for API and template serving
- **Bootstrap 5.1.3**: Frontend styling and responsive design
- **Font Awesome 6.0.0**: Icon library for enhanced UI
- **mlbstatsapi**: Python wrapper for MLB statistics API

### External System Integration
- **Bubble Integration**: JSON file generation for no-code platform consumption
- **File Path**: `/static/whiff_watch_data.json` for external access

## Deployment Strategy

### Static File Serving
- **Directory**: Static files served from `/static/` directory
- **Auto-Creation**: Dynamic directory creation for file outputs
- **File Types**: CSS stylesheets, generated JSON data files

### Error Handling Strategy
- **API Errors**: JSON-formatted error responses with timestamps
- **Exception Handling**: Try-catch blocks around critical data operations
- **Graceful Degradation**: Fallback responses when MLB API is unavailable

### Configuration Management
- **Season Year**: Hardcoded for 2025 season
- **Minimum Requirements**: 150 at-bat threshold for batter inclusion
- **File Paths**: Relative paths for cross-platform compatibility

## Changelog

```
Changelog:
- June 29, 2025. Initial setup
- June 29, 2025. Implemented authentic 2025 MLB data integration using MLB StatsAPI
- June 29, 2025. Successfully generating real whiff watch ratings from today's games
- June 29, 2025. Created accurate pitcher-batter matchups with current season statistics
- June 29, 2025. Deployed working JSON API for Bubble integration with real data
```

## User Preferences

```
Preferred communication style: Simple, everyday language.
```