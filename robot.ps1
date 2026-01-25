Add-Type -AssemblyName PresentationFramework
Add-Type -AssemblyName PresentationCore
Add-Type -AssemblyName WindowsBase
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$xaml = @"
<Window xmlns="http://schemas.microsoft.com/winfx/2000/xaml/presentation"
        xmlns:x="http://schemas.microsoft.com/winfx/2000/xaml"
        Title="AI Robot" Height="300" Width="400" 
        WindowStyle="None" AllowsTransparency="True" Background="Transparent" 
        Topmost="True" ShowInTaskbar="True" WindowStartupLocation="CenterScreen">
    
    <Border Name="MainBorder" CornerRadius="40" BorderThickness="3" Margin="20">
        <Border.Background>
            <LinearGradientBrush StartPoint="0,0" EndPoint="1,1">
                <GradientStop Color="#121212" Offset="0"/>
                <GradientStop Color="#1A1A2E" Offset="1"/>
            </LinearGradientBrush>
        </Border.Background>
        <Border.BorderBrush>
            <LinearGradientBrush StartPoint="0,0" EndPoint="1,1">
                <GradientStop Color="#00F2FF" Offset="0"/>
                <GradientStop Color="#7000FF" Offset="1"/>
            </LinearGradientBrush>
        </Border.BorderBrush>

        <Grid>
            <!-- Eyes Container -->
            <StackPanel Orientation="Horizontal" HorizontalAlignment="Center" VerticalAlignment="Top" Margin="0,60,0,0">
                <!-- Left Eye -->
                <Grid Margin="25,0">
                    <Ellipse Name="LeftEye" Width="50" Height="50" Fill="#00F2FF" />
                    <Ellipse Width="15" Height="15" Fill="White" HorizontalAlignment="Center" VerticalAlignment="Center" Margin="5,-5,0,0" Opacity="0.6"/>
                </Grid>

                <!-- Right Eye -->
                <Grid Margin="25,0">
                    <Ellipse Name="RightEye" Width="50" Height="50" Fill="#00F2FF" />
                    <Ellipse Width="15" Height="15" Fill="White" HorizontalAlignment="Center" VerticalAlignment="Center" Margin="5,-5,0,0" Opacity="0.6"/>
                </Grid>
            </StackPanel>

            <!-- Mouth -->
            <Grid VerticalAlignment="Bottom" HorizontalAlignment="Center" Margin="0,0,0,60">
                <Rectangle Name="Mouth" Width="140" Height="12" RadiusX="6" RadiusY="6" Fill="#00F2FF" />
            </Grid>
            
            <!-- Close Button -->
            <Button Name="CloseBtn" Content="×" HorizontalAlignment="Right" VerticalAlignment="Top" Margin="20" Background="Transparent" Foreground="White" BorderThickness="0" FontSize="20" Cursor="Hand"/>
        </Grid>
    </Border>
</Window>
"@

$reader = [System.XML.XmlReader]::Create([System.IO.StringReader]::new($xaml))
$Window = [System.Windows.Markup.XamlReader]::Load($reader)

# Find elements by Name
$MainBorder = $Window.FindName("MainBorder")
$LeftEye = $Window.FindName("LeftEye")
$RightEye = $Window.FindName("RightEye")
$Mouth = $Window.FindName("Mouth")
$CloseBtn = $Window.FindName("CloseBtn")

# Dragging logic
$MainBorder.Add_MouseLeftButtonDown({
    $Window.DragMove()
})

# Close logic
$CloseBtn.Add_Click({
    $Window.Close()
})

# Animation: Blinking
$blinkTimer = New-Object System.Windows.Threading.DispatcherTimer
$blinkTimer.Interval = [TimeSpan]::FromMilliseconds(4000)
$blinkTimer.Add_Tick({
    $innerTimer = New-Object System.Windows.Threading.DispatcherTimer
    $innerTimer.Interval = [TimeSpan]::FromMilliseconds(10)
    $step = 0
    $innerTimer.Add_Tick({
        if ($step -lt 10) {
            $LeftEye.Height = [Math]::Max(0.0, $LeftEye.Height - 5)
            $RightEye.Height = [Math]::Max(0.0, $RightEye.Height - 5)
        } elseif ($step -lt 20) {
            $LeftEye.Height = [Math]::Min(50.0, $LeftEye.Height + 5)
            $RightEye.Height = [Math]::Min(50.0, $RightEye.Height + 5)
        } else {
            $this.Stop()
        }
        $step++
    })
    $innerTimer.Start()
})
$blinkTimer.Start()

# Animation: Talk/Pulse
$talkTimer = New-Object System.Windows.Threading.DispatcherTimer
$talkTimer.Interval = [TimeSpan]::FromMilliseconds(150)
$talkTimer.Add_Tick({
    $height = 10 + (Get-Random -Minimum 0 -Maximum 10)
    $Mouth.Height = $height
})
$talkTimer.Start()

# Mouse Tracking
$trackTimer = New-Object System.Windows.Threading.DispatcherTimer
$trackTimer.Interval = [TimeSpan]::FromMilliseconds(20)
$trackTimer.Add_Tick({
    $mousePos = [System.Windows.Forms.Control]::MousePosition
    $winLeft = $Window.Left + ($Window.Width / 2)
    $winTop = $Window.Top + ($Window.Height / 3)
    
    $offsetX = ($mousePos.X - $winLeft) / 25
    $offsetY = ($mousePos.Y - $winTop) / 25
    
    $limit = 15.0
    $offsetX = [Math]::Max(-$limit, [Math]::Min($limit, $offsetX))
    $offsetY = [Math]::Max(-$limit, [Math]::Min($limit, $offsetY))
    
    $LeftEye.RenderTransform = New-Object System.Windows.Media.TranslateTransform($offsetX, $offsetY)
    $RightEye.RenderTransform = New-Object System.Windows.Media.TranslateTransform($offsetX, $offsetY)
})
$trackTimer.Start()

$Window.ShowDialog() | Out-Null
