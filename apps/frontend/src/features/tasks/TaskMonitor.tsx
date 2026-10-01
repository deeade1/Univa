import { useSubscription } from '@apollo/client';
import { TASK_STATUS_SUBSCRIPTION } from '@/lib/apollo/subscriptions';

interface TaskMonitorProps {
  taskId: string;
}

export default function TaskMonitor({ taskId }: TaskMonitorProps) {
  const { data } = useSubscription(TASK_STATUS_SUBSCRIPTION, {
    variables: { taskId }
  });

  return (
    <div>
      <h3>Task Status: {data?.taskStatus.state}</h3>
      {data?.taskStatus.progress && (
        <progress value={data.taskStatus.progress} max="100" />
      )}
    </div>
  );
}