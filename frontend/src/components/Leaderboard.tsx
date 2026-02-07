import { useState, useEffect } from "react";
import { config } from "../config";

interface LeaderboardEntry {
  name: string;
  completed: number;
}

export function Leaderboard() {
  const [entries, setEntries] = useState<LeaderboardEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${config.apiUrl}/api/leaderboard`)
      .then((r) => r.json())
      .then((data) => setEntries(data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="leaderboard">Loading leaderboard...</div>;
  if (entries.length === 0) return null; // Don't show if empty/offline

  return (
    <div className="leaderboard">
      <h3>Leaderboard</h3>
      <table>
        <thead>
          <tr>
            <th>#</th>
            <th>Name</th>
            <th>Completed</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((entry, i) => (
            <tr key={i}>
              <td>{i + 1}</td>
              <td>{entry.name}</td>
              <td>{entry.completed} / 11</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
