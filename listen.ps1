Add-Type -AssemblyName System.Speech
$culture = New-Object System.Globalization.CultureInfo("en-US")
$recognizer = New-Object System.Speech.Recognition.SpeechRecognitionEngine($culture)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

try {
    $recognizer.SetInputToDefaultAudioDevice()
    [Console]::WriteLine("STATUS: INITIALIZED - Culture en-US - Default Device Set")
} catch {
    [Console]::WriteLine("STATUS: ERROR_INIT - $($_.Exception.Message)")
}

$choices = New-Object System.Speech.Recognition.Choices
$choices.Add(@("hello", "name", "who are you", "how are you", "shut down", "power off", "hey robot"))
$gb = New-Object System.Speech.Recognition.GrammarBuilder
$gb.Append($choices)
$grammar = New-Object System.Speech.Recognition.Grammar($gb)
$recognizer.LoadGrammar($grammar)

$dictation = New-Object System.Speech.Recognition.DictationGrammar
$recognizer.LoadGrammar($dictation)

$recognizer.add_SpeechDetected({
    [Console]::WriteLine("STATUS: HEARING_ACTIVITY")
})

$recognizer.add_SpeechRecognized({
    param($s, $e)
    [Console]::WriteLine("HEARD: $($e.Result.Text) (Conf: $($e.Result.Confidence))")
})

$recognizer.add_SpeechRecognitionRejected({
    param($s, $e)
    [Console]::WriteLine("STATUS: REJECTED (Level: $($recognizer.AudioLevel), Conf: $($e.Result.Confidence))")
})

# Start Recognition
try {
    $recognizer.RecognizeAsync([System.Speech.Recognition.RecognizeMode]::Multiple)
    [Console]::WriteLine("STATUS: LISTENING")
} catch {
    [Console]::WriteLine("STATUS: ERROR_START - $($_.Exception.Message)")
}

try {
    while($true) {
        $level = $recognizer.AudioLevel
        $timestamp = Get-Date -Format "HH:mm:ss.fff"
        [Console]::WriteLine("STATUS: AUDIO_LEVEL: $level [$timestamp]")
        Start-Sleep -Milliseconds 250
    }
} catch {
    [Console]::WriteLine("STATUS: ERROR_LOOP - $($_.Exception.Message)")
} finally {
    [Console]::WriteLine("STATUS: SCRIPT_EXITING")
}

