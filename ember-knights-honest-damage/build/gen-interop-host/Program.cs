// GenInteropHost: calls Il2CppInterop.Generator 1.4.6 (BepInEx-bundled) to produce proxy assemblies.
// This ensures the compile-time proxy surface matches what BepInEx regenerates at game start.
//
// Usage: GenInteropHost <dummyDllsDir> <outputDir> <unityLibsDir> <gameAssemblyPath>

using Il2CppInterop.Generator;
using Il2CppInterop.Generator.MetadataAccess;
using Il2CppInterop.Generator.Runners;

if (args.Length < 4)
{
    Console.Error.WriteLine("Usage: GenInteropHost <dummyDllsDir> <outputDir> <unityLibsDir> <gameAssemblyPath>");
    return 1;
}

var dummyDllsDir     = args[0];
var outputDir        = args[1];
var unityLibsDir     = args[2];
var gameAssemblyPath = args[3];

if (!Directory.Exists(dummyDllsDir))   { Console.Error.WriteLine($"ERROR: dummyDllsDir not found: {dummyDllsDir}"); return 2; }
if (!Directory.Exists(unityLibsDir))   { Console.Error.WriteLine($"ERROR: unityLibsDir not found: {unityLibsDir}"); return 2; }
if (!File.Exists(gameAssemblyPath))    { Console.Error.WriteLine($"ERROR: gameAssembly not found: {gameAssemblyPath}"); return 2; }

Directory.CreateDirectory(outputDir);

var inputPaths = Directory.GetFiles(dummyDllsDir, "*.dll").ToList();
var unityPaths = Directory.GetFiles(unityLibsDir, "*.dll").ToList();

Console.WriteLine("[GenInteropHost] Generator : Il2CppInterop.Generator 1.4.6 + v31-capable LibCpp2IL (BepInEx be.735 bundle)");
Console.WriteLine($"[GenInteropHost] Input DLLs: {inputPaths.Count} from {dummyDllsDir}");
Console.WriteLine($"[GenInteropHost] Unity libs: {unityPaths.Count} from {unityLibsDir}");
Console.WriteLine($"[GenInteropHost] Output    : {outputDir}");
Console.WriteLine($"[GenInteropHost] Game DLL  : {gameAssemblyPath}");

// CecilMetadataAccess(IEnumerable<string>) handles assembly loading and resolution internally.
// We pass input paths as strings; it sets up a Mono.Cecil resolver over that directory.
using var gameAssemblies  = new CecilMetadataAccess(inputPaths);
using var unityAssemblies = new CecilMetadataAccess(unityPaths);

// GeneratorOptions.Source in 1.4.6 is List<Mono.Cecil.AssemblyDefinition> — populated by the
// CecilMetadataAccess.Assemblies property, not set manually.
var opts = new GeneratorOptions
{
    Source           = gameAssemblies.Assemblies.ToList(),
    OutputDir        = outputDir,
    UnityBaseLibsDir = unityLibsDir,
    GameAssemblyPath = gameAssemblyPath,
    Parallel         = true,
    Verbose          = false,
};

var gen = Il2CppInteropGenerator.Create(opts);
InteropAssemblyGenerator.AddInteropAssemblyGenerator(gen);
gen.Run();

Console.WriteLine($"[GenInteropHost] Done. Output files: {Directory.GetFiles(outputDir, "*.dll").Length}");
return 0;
