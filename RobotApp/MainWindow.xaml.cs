using System;
using System.Windows;
using System.Windows.Input;
using System.Windows.Threading;
using System.Windows.Media;

namespace RobotApp
{
    public partial class MainWindow : Window
    {
        private DispatcherTimer _blinkTimer;
        private DispatcherTimer _talkTimer;
        private DispatcherTimer _trackTimer;
        private Random _random = new Random();

        private DispatcherTimer _glowTimer;
        private double _glowOpacity = 0.8;
        private bool _glowIncreasing = false;

        public MainWindow()
        {
            InitializeComponent();
            SetupTimers();
        }

        private void SetupTimers()
        {
            // Glow Pulse
            _glowTimer = new DispatcherTimer();
            _glowTimer.Interval = TimeSpan.FromMilliseconds(50);
            _glowTimer.Tick += (s, e) => {
                if (_glowIncreasing) {
                    _glowOpacity += 0.02;
                    if (_glowOpacity >= 0.9) _glowIncreasing = false;
                } else {
                    _glowOpacity -= 0.02;
                    if (_glowOpacity <= 0.6) _glowIncreasing = true;
                }
                var brush = new SolidColorBrush(Color.FromRgb(0, 242, 255));
                brush.Opacity = _glowOpacity;
                LeftEye.Fill = brush;
                RightEye.Fill = brush;
            };
            _glowTimer.Start();
            // Blinking
            _blinkTimer = new DispatcherTimer();
            _blinkTimer.Interval = TimeSpan.FromMilliseconds(4000);
            _blinkTimer.Tick += (s, e) => Blink();
            _blinkTimer.Start();

            // Talking (Pulse)
            _talkTimer = new DispatcherTimer();
            _talkTimer.Interval = TimeSpan.FromMilliseconds(150);
            _talkTimer.Tick += (s, e) => {
                Mouth.Height = 10 + _random.Next(0, 10);
            };
            _talkTimer.Start();

            // Mouse Tracking
            _trackTimer = new DispatcherTimer();
            _trackTimer.Interval = TimeSpan.FromMilliseconds(20);
            _trackTimer.Tick += (s, e) => TrackMouse();
            _trackTimer.Start();
        }

        private async void Blink()
        {
            for (int i = 0; i < 5; i++)
            {
                LeftEye.Height -= 10;
                RightEye.Height -= 10;
                await System.Threading.Tasks.Task.Delay(10);
            }
            for (int i = 0; i < 5; i++)
            {
                LeftEye.Height += 10;
                RightEye.Height += 10;
                await System.Threading.Tasks.Task.Delay(10);
            }
        }

        private void TrackMouse()
        {
            Point mousePos = PointToScreen(Mouse.GetPosition(this));
            double winCenterX = Left + Width / 2;
            double winCenterY = Top + Height / 3;

            double offsetX = (mousePos.X - winCenterX) / 25;
            double offsetY = (mousePos.Y - winCenterY) / 25;

            double limit = 15;
            offsetX = Math.Max(-limit, Math.Min(limit, offsetX));
            offsetY = Math.Max(-limit, Math.Min(limit, offsetY));

            LeftEyeTransform.X = offsetX;
            LeftEyeTransform.Y = offsetY;
            RightEyeTransform.X = offsetX;
            RightEyeTransform.Y = offsetY;
        }

        private void Window_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
        {
            if (e.LeftButton == MouseButtonState.Pressed)
                DragMove();
        }

        private void CloseButton_Click(object sender, RoutedEventArgs e)
        {
            Close();
        }
    }
}