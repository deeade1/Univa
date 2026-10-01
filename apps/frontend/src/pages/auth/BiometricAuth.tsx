// components/auth/BiometricAuth.tsx
import React from 'react';
import { Button, ListGroup } from 'react-bootstrap';
import { DeviceInfo } from '@/context/authTypes';

interface BiometricAuthProps {
  devices: DeviceInfo[];
  onSelectDevice: (deviceId: string) => void;
  onBackToPassword: () => void;
}

export const BiometricAuth: React.FC<BiometricAuthProps> = ({
  devices,
  onSelectDevice,
  onBackToPassword
}) => (
  <div className="biometric-auth">
    <h3 className="text-center">Biometric Login</h3>
    <p className="text-center">Use your registered biometric device</p>
    
    <ListGroup className="mb-3">
      {devices.map(device => (
        <ListGroup.Item
          key={device.id}
          action
          onClick={() => onSelectDevice(device.id)}
          className="d-flex justify-content-between align-items-center"
        >
          {device.name}
          <span className="badge bg-light text-dark">
            Last used: {device.lastUsed && new Date(device.lastUsed).toLocaleDateString()}
          </span>
        </ListGroup.Item>
      ))}
    </ListGroup>
    
    <div className="text-center">
      <Button 
        variant="secondary"
        onClick={onBackToPassword}
      >
        Back to Password
      </Button>
    </div>
  </div>
);