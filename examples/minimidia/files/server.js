const express = require('express');
const Database = require('better-sqlite3');
const helmet = require('helmet');
const compression = require('compression');
const morgan = require('morgan');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3000;
const DB_PATH = process.env.DB_PATH || './data/minimidia.db';

app.use(helmet());
app.use(compression());
app.use(morgan('combined'));
app.use(express.json());

const db = new Database(DB_PATH);
db.exec('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, email TEXT, name TEXT)');

app.get('/health', (req, res) => res.json({ status: 'healthy', uptime: process.uptime() }));
app.get('/', (req, res) => res.json({ message: 'Minimidia SaaS', version: '1.0.0' }));

app.listen(PORT, '127.0.0.1', () => console.log('Minimidia started on port', PORT));
