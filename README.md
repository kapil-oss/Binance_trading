# AlsaTrade Mobile App

A React Native mobile app for trading dashboard management, built with Expo for easy development and deployment.

## Features

- **Dashboard**: Real-time trading metrics and strategy overview
- **Executions**: View trade execution history and status
- **Settings**: Configure trading preferences and account settings
- **Dark Theme**: Modern dark UI optimized for mobile
- **Real-time Updates**: Live data synchronization with backend

## Prerequisites

- Node.js (v16 or higher)
- npm or yarn
- Expo CLI (`npm install -g @expo/cli`)
- Expo Go app on your mobile device
- AlsaTrade Backend running (Python FastAPI)

## Setup Instructions

### 1. Install Dependencies

```bash
npm install
```

### 2. Configure Backend URL

Edit `src/services/api.js` and update the `API_BASE_URL`:

```javascript
const API_BASE_URL = 'http://YOUR_BACKEND_IP:8000'; // Replace with your backend URL
```

**Important**: If running on mobile device, use your computer's IP address, not `localhost`.

### 3. Start the Development Server

```bash
npm start
```

This will start the Expo development server and show a QR code.

### 4. Run on Mobile Device

1. Install **Expo Go** app from App Store (iOS) or Google Play (Android)
2. Scan the QR code with your device camera (iOS) or Expo Go app (Android)
3. The app will load and connect to your backend

## Project Structure

```
├── App.js                 # Main app entry point
├── app.json              # Expo configuration
├── src/
│   ├── components/       # Reusable UI components
│   │   ├── MetricCard.js
│   │   ├── ConnectionStatus.js
│   │   └── SettingsCard.js
│   ├── context/          # React context for state management
│   │   └── TradingContext.js
│   ├── screens/          # App screens
│   │   ├── DashboardScreen.js
│   │   ├── ExecutionsScreen.js
│   │   └── SettingsScreen.js
│   ├── services/         # API and utility services
│   │   └── api.js
│   └── theme/            # App theme and styling
│       └── theme.js
└── assets/               # App icons and images
```

## Available Scripts

- `npm start` - Start Expo development server
- `npm run android` - Start with Android device/emulator
- `npm run ios` - Start with iOS simulator
- `npm run web` - Start web version

## Backend Integration

The app connects to the AlsaTrade Python backend API. Ensure your backend is running and accessible:

1. Start your Python FastAPI backend
2. Update the API URL in `src/services/api.js`
3. Ensure your mobile device can reach the backend (same network)

### API Endpoints Used

- `GET /preferences/options` - Get available trading options
- `GET /preferences/current` - Get current user preferences
- `POST /preferences/*` - Update trading preferences
- `GET /account/summary` - Get account balance information
- `GET /executions` - Get trade execution history

## Customization

### Theme Colors

Edit `src/theme/theme.js` to customize the app's color scheme:

```javascript
export const colors = {
  background: '#030712',
  accent: '#38bdf8',
  // ... other colors
};
```

### Navigation

Modify `App.js` to add new screens or change navigation structure.

### Components

Add new components in `src/components/` and import them in your screens.

## Troubleshooting

### Common Issues

1. **Can't connect to backend**
   - Ensure backend is running
   - Check if mobile device is on same network
   - Use IP address instead of localhost
   - Check firewall settings

2. **App won't load**
   - Clear Expo cache: `expo start -c`
   - Restart Expo development server
   - Check for JavaScript errors in console

3. **Missing dependencies**
   - Run `npm install` again
   - Clear node_modules: `rm -rf node_modules && npm install`

### Network Configuration

For local development, your mobile device needs to reach your backend server:

1. Find your computer's IP address:
   - Windows: `ipconfig`
   - Mac/Linux: `ifconfig`

2. Update API_BASE_URL to use this IP:
   ```javascript
   const API_BASE_URL = 'http://192.168.1.100:8000'; // Example IP
   ```

3. Ensure your backend accepts connections from your IP

## Building for Production

### Android

```bash
expo build:android
```

### iOS

```bash
expo build:ios
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test on both iOS and Android
5. Submit a pull request

## License

This project is licensed under the MIT License.