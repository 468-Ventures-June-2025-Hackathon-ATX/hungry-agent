import React, { useState, useEffect } from 'react';
import { MapPin, Save, Edit3 } from 'lucide-react';

const DeliverySettings = ({ onAddressChange }) => {
  const [address, setAddress] = useState('');
  const [isEditing, setIsEditing] = useState(false);
  const [savedAddress, setSavedAddress] = useState('');

  // Load saved address from localStorage on component mount
  useEffect(() => {
    const saved = localStorage.getItem('deliveryAddress');
    if (saved) {
      setAddress(saved);
      setSavedAddress(saved);
      onAddressChange(saved);
    } else {
      setIsEditing(true); // Show edit mode if no address is saved
    }
  }, [onAddressChange]);

  const handleSave = () => {
    if (address.trim()) {
      localStorage.setItem('deliveryAddress', address.trim());
      setSavedAddress(address.trim());
      setIsEditing(false);
      onAddressChange(address.trim());
    }
  };

  const handleEdit = () => {
    setIsEditing(true);
  };

  const handleCancel = () => {
    setAddress(savedAddress);
    setIsEditing(false);
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleSave();
    } else if (e.key === 'Escape') {
      handleCancel();
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <MapPin className="w-5 h-5 text-blue-600" />
          <h3 className="text-lg font-semibold text-gray-800">Delivery Address</h3>
        </div>
        {!isEditing && savedAddress && (
          <button
            onClick={handleEdit}
            className="flex items-center space-x-1 text-blue-600 hover:text-blue-700 text-sm"
          >
            <Edit3 className="w-4 h-4" />
            <span>Edit</span>
          </button>
        )}
      </div>

      {isEditing ? (
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Enter your delivery address:
            </label>
            <input
              type="text"
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="e.g., 123 Main St, San Francisco, CA 94103"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              autoFocus
            />
          </div>
          <div className="flex space-x-2">
            <button
              onClick={handleSave}
              disabled={!address.trim()}
              className="flex items-center space-x-1 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Save className="w-4 h-4" />
              <span>Save Address</span>
            </button>
            {savedAddress && (
              <button
                onClick={handleCancel}
                className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50"
              >
                Cancel
              </button>
            )}
          </div>
        </div>
      ) : (
        <div className="space-y-2">
          {savedAddress ? (
            <div className="flex items-start space-x-2">
              <div className="flex-1">
                <div className="text-gray-800 font-medium">{savedAddress}</div>
                <div className="text-sm text-gray-500 mt-1">
                  This address will be used for all taco deliveries
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-4">
              <div className="text-gray-500 mb-2">No delivery address set</div>
              <button
                onClick={() => setIsEditing(true)}
                className="text-blue-600 hover:text-blue-700 text-sm"
              >
                Add delivery address
              </button>
            </div>
          )}
        </div>
      )}

      {savedAddress && (
        <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded-md">
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 bg-green-500 rounded-full"></div>
            <span className="text-sm text-green-700">
              Address configured - ready for voice orders!
            </span>
          </div>
        </div>
      )}
    </div>
  );
};

export default DeliverySettings;
