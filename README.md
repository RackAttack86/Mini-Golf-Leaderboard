# Mini Golf Leaderboard

A web-based mini golf scoring application built with Flask. Track scores for multiple players across unlimited rounds and courses, with comprehensive statistics and analytics.

## Features

### Core Features
- **Player Management**: Add, edit, and manage multiple players
- **Course Database**: Pre-loaded with all 37 Walkabout Mini Golf courses
- **Round Tracking**: Record and edit rounds with multiple players and their scores
- **Golf Scoring**: Supports negative scores (relative to par), lowest score wins
- **Trophy System**: Visual rewards for 1st (gold), 2nd (silver), 3rd (bronze), and 4th place

### Statistics & Analysis
- **Leaderboard**: Player rankings by average finishing position
- **Course Statistics**: Compare difficulty, popularity, and see best/worst scores with player names
- **Historical Trends**: Track player improvement over time with interactive charts
- **Head-to-Head Comparison**: Compare two players directly

### Technical Features
- JSON file-based storage with atomic writes
- Thread-safe data operations
- Client-side and server-side validation
- Responsive Bootstrap 5 UI
- Interactive Chart.js visualizations
- Soft delete for data integrity

## Installation

1. Clone this repository:
```bash
git clone <your-repo-url>
cd Mini-Golf-Leaderboard
```

2. Install Python 3.12 or higher

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up data directory:
```bash
# On Windows
xcopy /E /I data-example data

# On Mac/Linux
cp -r data-example data
```

This creates your local data directory with pre-loaded Walkabout Mini Golf courses.

## Usage

1. Start the application:
```bash
python app.py
```

2. Open your browser and navigate to:
```
http://127.0.0.1:5000
```

3. Start by:
   - Adding players (Players > Add Player)
   - Adding courses (Courses > Add Course)
   - Recording rounds (Rounds > Add Round)

## Project Structure

```
Mini-Golf-Leaderboard/
├── app.py                 # Flask application entry point
├── config.py             # Application configuration
├── requirements.txt      # Python dependencies
├── data/                 # JSON data storage
├── models/               # Data models and storage
├── services/             # Business logic and statistics
├── routes/               # Flask route handlers
├── templates/            # HTML templates
├── static/               # CSS, JavaScript, images
└── utils/                # Utility functions
```

## Data Storage

All data is stored in JSON files in the `data/` directory:
- `players.json` - Player records
- `courses.json` - Course records
- `rounds.json` - Round/score records

Data is persisted automatically with atomic writes to prevent corruption.

## Features by Page

### Dashboard (/)
- Quick stats (total players, courses, rounds)
- Top 3 players
- Recent rounds

### Players
- List all players
- Add new players
- View player details and statistics
- Edit player information
- Delete/deactivate players

### Courses
- List all courses
- Add new courses
- View course details and statistics
- Edit course information
- Delete/deactivate courses

### Rounds
- List all rounds with filtering
- Add new rounds with multiple players
- View round details
- Delete rounds

### Statistics
- **Leaderboard**: Rankings with multiple sort options
- **Course Stats**: Difficulty rankings and popularity
- **Trends**: Player improvement tracking with charts
- **Head-to-Head**: Direct player comparisons

## Technologies Used

- **Backend**: Flask 3.0.0, Python 3.12
- **Frontend**: Bootstrap 5, Chart.js 4.4.0
- **Data Storage**: JSON files with atomic writes
- **Styling**: Custom CSS with golf-themed colors

## Development

The application runs in debug mode by default. For production deployment:
1. Set `DEBUG = False` in `config.py`
2. Use a production WSGI server (e.g., Gunicorn, uWSGI)
3. Set a secure `SECRET_KEY` environment variable

## License

This project was created for tracking mini golf scores among friends and family.

## Contributing

Feel free to fork this project and customize it for your own use!
