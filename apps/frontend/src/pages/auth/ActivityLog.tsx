// components/ActivityLog.tsx
import React from 'react';
import { useAuth } from '@/context/authContext';
import { AuthEvent } from '@/context/authTypes';

export const ActivityLog: React.FC = () => {
  const { user } = useAuth();
  const [activities, setActivities] = React.useState<AuthEvent[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState('');

  React.useEffect(() => {
    const fetchActivities = async () => {
      try {
        // Replace with your actual API call
        const response = await fetch('/api/auth/activities', {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        });

        if (response.ok) {
          const data = await response.json();
          setActivities(data.activities);
        } else {
          setError('Failed to load activities');
        }
      } catch (err) {
        setError('Network error loading activities');
      } finally {
        setLoading(false);
      }
    };

    if (user) fetchActivities();
  }, [user]);

  if (loading) return <div>Loading activity log...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <div className="activity-log">
      <h3>Security Activity Log</h3>
      <div className="table-responsive">
        <table className="table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Activity</th>
              <th>Service</th>
              <th>Device</th>
            </tr>
          </thead>
          <tbody>
            {activities.map((activity, index) => (
              <tr key={index}>
                <td>{new Date(activity.timestamp).toLocaleString()}</td>
                <td>{activity.type}</td>
                <td>{activity.service || 'N/A'}</td>
                <td>{activity.device?.name || 'Unknown'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};