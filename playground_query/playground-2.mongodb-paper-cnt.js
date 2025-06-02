/* global use, db */
// MongoDB Playground
// Use Ctrl+Space inside a snippet or a string literal to trigger completions.

// The current database to use.
use('arxiv_papers');

// Search for documents in the current collection.
db.papers.aggregate([
    { $unwind: "$categories" },
    {
      $group: {
        _id: "$categories",
        count: { $sum: 1 }
      }
    },
    { $sort: { count: -1 } } // Optional: sort by count descending
  ])
  ;
