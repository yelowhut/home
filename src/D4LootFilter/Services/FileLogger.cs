using System.IO;

namespace D4LootFilter.Services;

public class FileLogger : IDisposable
{
    private readonly StreamWriter _writer;
    private readonly string _logDir;
    private const int MaxLogFiles = 50;

    public FileLogger(string logDir)
    {
        _logDir = logDir;
        Directory.CreateDirectory(logDir);
        CleanOldLogs();

        var fileName = $"d4lf-{DateTime.Now:yyyy-MM-dd_HH-mm-ss}.log";
        var path = Path.Combine(logDir, fileName);
        _writer = new StreamWriter(path, append: false) { AutoFlush = true };
        _writer.WriteLine($"[{DateTime.Now:HH:mm:ss.fff}] Log started");
    }

    public void Log(string message)
    {
        var line = $"[{DateTime.Now:HH:mm:ss.fff}] {message}";
        _writer.WriteLine(line);
        Console.WriteLine(line);
    }

    private void CleanOldLogs()
    {
        var files = Directory.GetFiles(_logDir, "d4lf-*.log")
            .OrderByDescending(f => f)
            .Skip(MaxLogFiles - 1)
            .ToArray();
        foreach (var f in files)
        {
            try { File.Delete(f); } catch { }
        }
    }

    public void Dispose()
    {
        _writer.Dispose();
    }
}
