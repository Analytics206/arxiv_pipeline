// MongoDB Playground
// Use Ctrl+Space inside a snippet or a string literal to trigger completions.

// The current database to use.
use("arxiv_papers");

// Find a document in a collection.
db.papers.aggregate([
    { $match: {} }, // Optional, can filter if needed
    { $out: "papers_06_01_2025" }
  ]) ;
