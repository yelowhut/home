using Microsoft.Playwright;
using System.Text;
using System.Text.Json;

const string OutputDir = @"D:\git\home\spikes\MobalyticsSpike";
const string BaseUrl = "https://mobalytics.gg/diablo-4/builds/barbarian-whirl-wind-barb";
const string UserAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36";

Console.WriteLine("=== Mobalytics Scraping Spike - Final ===");
Console.WriteLine($"Starting at {DateTime.Now}");
Console.WriteLine();

// Phase 0: Test direct HTTP (no browser)
await DirectApiTest.RunAsync();

// Phase 1: Test headless Chromium with DOMContentLoaded (not NetworkIdle)
Console.WriteLine("\n=== Phase 1: Headless Chromium with DOMContentLoaded ===\n");

using var playwright = await Playwright.CreateAsync();

await using var browser = await playwright.Chromium.LaunchAsync(new BrowserTypeLaunchOptions
{
    Headless = true,
    Args = new[] { "--disable-blink-features=AutomationControlled" }
});

var context = await browser.NewContextAsync(new BrowserNewContextOptions
{
    UserAgent = UserAgent,
    ViewportSize = new ViewportSize { Width = 1920, Height = 1080 },
    Locale = "en-US",
});

var graphqlResponses = new List<(string url, int status, string body)>();
var page = await context.NewPageAsync();

// Capture GraphQL response bodies
page.Response += async (_, response) =>
{
    if (response.Url.Contains("graphql"))
    {
        try
        {
            var body = await response.TextAsync();
            lock (graphqlResponses)
            {
                graphqlResponses.Add((response.Url, response.Status, body));
            }
        }
        catch { }
    }
};

try
{
    Console.WriteLine("[headless] Navigating with DOMContentLoaded...");
    var navResponse = await page.GotoAsync(BaseUrl, new PageGotoOptions
    {
        WaitUntil = WaitUntilState.DOMContentLoaded,
        Timeout = 30000
    });
    Console.WriteLine($"[headless] Status: {navResponse?.Status}");
    Console.WriteLine($"[headless] Title: {await page.TitleAsync()}");

    // Wait for GraphQL responses to come back
    Console.WriteLine("[headless] Waiting for GraphQL data...");
    await page.WaitForTimeoutAsync(8000);

    // Check for bot protection
    var title = await page.TitleAsync();
    var bodyText = await page.InnerTextAsync("body");
    var isBlocked = bodyText.Contains("Checking your browser") || bodyText.Contains("Just a moment") ||
                    title.Contains("Just a moment");
    Console.WriteLine($"[headless] Blocked by bot protection: {isBlocked}");

    // Take screenshot
    await page.ScreenshotAsync(new PageScreenshotOptions
    {
        Path = Path.Combine(OutputDir, "headless-screenshot.png"),
        FullPage = true
    });
    Console.WriteLine("[headless] Screenshot saved to headless-screenshot.png");

    // Report GraphQL captures
    Console.WriteLine($"[headless] GraphQL responses captured: {graphqlResponses.Count}");

    if (graphqlResponses.Count > 0)
    {
        Console.WriteLine("[headless] *** HEADLESS MODE WORKS ***");

        // Find the main build data response (largest one)
        var mainResponse = graphqlResponses.OrderByDescending(r => r.body.Length).First();
        Console.WriteLine($"[headless] Largest response: {mainResponse.body.Length} chars");

        // Save it
        await File.WriteAllTextAsync(
            Path.Combine(OutputDir, "headless-graphql-response.json"),
            JsonPrettify(mainResponse.body));

        // Parse and extract build data
        Console.WriteLine("\n=== Phase 2: Extracting Build Data from GraphQL Response ===\n");
        await ExtractBuildData(mainResponse.body);
    }
    else
    {
        Console.WriteLine("[headless] No GraphQL data captured - trying from saved file...");

        // Fall back to previously saved response
        var savedPath = Path.Combine(OutputDir, "graphql-4-Diablo4TakeoverQuery-response.json");
        if (File.Exists(savedPath))
        {
            var savedJson = await File.ReadAllTextAsync(savedPath);
            Console.WriteLine($"[fallback] Loaded saved response ({savedJson.Length} chars)");
            Console.WriteLine("\n=== Phase 2: Extracting Build Data from Saved Response ===\n");
            await ExtractBuildData(savedJson);
        }
    }
}
catch (Exception ex)
{
    Console.WriteLine($"[headless] ERROR: {ex.GetType().Name}: {ex.Message}");

    // Fall back to saved data
    var savedPath = Path.Combine(OutputDir, "graphql-4-Diablo4TakeoverQuery-response.json");
    if (File.Exists(savedPath))
    {
        var savedJson = await File.ReadAllTextAsync(savedPath);
        Console.WriteLine($"\n[fallback] Using saved GraphQL response ({savedJson.Length} chars)");
        Console.WriteLine("\n=== Phase 2: Extracting Build Data from Saved Response ===\n");
        await ExtractBuildData(savedJson);
    }
}

Console.WriteLine("\n=== Spike Complete ===");

// === BUILD DATA EXTRACTOR ===
async Task ExtractBuildData(string jsonResponse)
{
    var doc = JsonDocument.Parse(jsonResponse);
    var root = doc.RootElement;

    // Navigate to build data
    var buildData = root
        .GetProperty("data")
        .GetProperty("game")
        .GetProperty("documents")
        .GetProperty("userGeneratedDocumentBySlug")
        .GetProperty("data");

    var buildName = buildData.GetProperty("data").GetProperty("name").GetString();
    var buildSlug = buildData.GetProperty("slugifiedName").GetString();
    Console.WriteLine($"Build: {buildName} (slug: {buildSlug})");
    Console.WriteLine();

    // Get variant names from content section
    var variantNames = new Dictionary<string, string>();
    if (buildData.TryGetProperty("content", out var content))
    {
        foreach (var widget in content.EnumerateArray())
        {
            var typename = widget.GetProperty("__typename").GetString();
            if (typename == "NgfDocumentCmWidgetContentVariantsV1")
            {
                var variants = widget.GetProperty("data").GetProperty("childrenVariants");
                foreach (var v in variants.EnumerateArray())
                {
                    var vid = v.GetProperty("id").GetString() ?? "";
                    var vtitle = v.GetProperty("title").GetString() ?? "";
                    variantNames[vid] = vtitle;
                }
            }
        }
    }

    // Extract build variants with equipment
    var buildVariants = buildData.GetProperty("data").GetProperty("buildVariants").GetProperty("values");

    Console.WriteLine($"Total Build Variants: {buildVariants.GetArrayLength()}");
    Console.WriteLine("Variant IDs and Names:");
    foreach (var variant in buildVariants.EnumerateArray())
    {
        var variantId = variant.GetProperty("id").GetString() ?? "";
        var variantName = variantNames.GetValueOrDefault(variantId, "(unnamed)");
        Console.WriteLine($"  ID={variantId}: {variantName}");
    }
    Console.WriteLine();
    Console.WriteLine("NOTE: All variants are returned in a single GraphQL response.");
    Console.WriteLine("The ?ws-ngf5-1=activeVariantId URL param is client-side tab state only.");
    Console.WriteLine();

    // Detailed extraction for each variant
    foreach (var variant in buildVariants.EnumerateArray())
    {
        var variantId = variant.GetProperty("id").GetString() ?? "";
        var variantName = variantNames.GetValueOrDefault(variantId, "(unnamed)");
        Console.WriteLine($"========================================");
        Console.WriteLine($"VARIANT {variantId}: {variantName}");
        Console.WriteLine($"========================================");

        if (!variant.TryGetProperty("genericBuilder", out var builder))
        {
            Console.WriteLine("  (no genericBuilder data)");
            continue;
        }

        var slots = builder.GetProperty("slots");
        foreach (var slot in slots.EnumerateArray())
        {
            var slotSlug = slot.GetProperty("gameSlotSlug").GetString();
            var entity = slot.GetProperty("gameEntity");

            var itemTitle = entity.GetProperty("title").GetString();
            var itemType = entity.GetProperty("type").GetString();
            var itemSlug = entity.GetProperty("slug").GetString();

            // Check if mythic/chaos/unique
            var entityInfo = "";
            if (entity.TryGetProperty("entity", out var entityDetail) &&
                entityDetail.ValueKind == JsonValueKind.Object)
            {
                if (entityDetail.TryGetProperty("__typename", out var tn))
                {
                    var entityType = tn.GetString();
                    if (entityType == "D4UniqueItem")
                    {
                        var mythic = entityDetail.TryGetProperty("mythic", out var m) && m.ValueKind == JsonValueKind.True;
                        var chaos = entityDetail.TryGetProperty("chaos", out var c) && c.ValueKind == JsonValueKind.True;
                        entityInfo = mythic ? " [MYTHIC]" : chaos ? " [CHAOS]" : " [UNIQUE]";
                    }
                    else if (entityType == "D4Aspect")
                    {
                        entityInfo = " [ASPECT]";
                    }
                    else if (entityType == "D4ChaosPerk")
                    {
                        entityInfo = " [CHAOS PERK]";
                    }
                }
            }

            Console.WriteLine($"\n  {slotSlug}: {itemTitle}{entityInfo}");
            Console.WriteLine($"    Type: {itemType} | Slug: {itemSlug}");

            if (!entity.TryGetProperty("modifiers", out var modifiers) ||
                modifiers.ValueKind != JsonValueKind.Object)
                continue;

            // Gear stats (affixes)
            if (modifiers.TryGetProperty("gearStats", out var gearStats) &&
                gearStats.ValueKind == JsonValueKind.Array)
            {
                Console.Write("    Affixes:");
                var affixList = new List<string>();
                foreach (var stat in gearStats.EnumerateArray())
                {
                    if (stat.ValueKind != JsonValueKind.Object) continue;
                    if (!stat.TryGetProperty("id", out var idEl)) continue;
                    var statId = idEl.GetString() ?? "";
                    var isGreater = stat.TryGetProperty("isGreater", out var g) && g.ValueKind == JsonValueKind.True;
                    var isMasterwork = stat.TryGetProperty("isMasterwork", out var mw) && mw.ValueKind == JsonValueKind.True;

                    var markers = "";
                    if (isGreater) markers += " [GA]";
                    if (isMasterwork) markers += " [MW]";

                    affixList.Add($"{statId}{markers}");
                }
                Console.WriteLine($" {string.Join(", ", affixList)}");
            }

            // Implicit stats
            if (modifiers.TryGetProperty("implicitStats", out var implicitStats) &&
                implicitStats.ValueKind == JsonValueKind.Array)
            {
                var implicits = new List<string>();
                foreach (var stat in implicitStats.EnumerateArray())
                {
                    if (stat.ValueKind == JsonValueKind.Null) continue;
                    if (stat.TryGetProperty("id", out var id))
                        implicits.Add(id.GetString() ?? "");
                }
                if (implicits.Count > 0)
                    Console.WriteLine($"    Implicits: {string.Join(", ", implicits)}");
            }

            // Socket stats
            if (modifiers.TryGetProperty("socketStats", out var socketStats) &&
                socketStats.ValueKind == JsonValueKind.Array)
            {
                var sockets = new List<string>();
                foreach (var socket in socketStats.EnumerateArray())
                {
                    if (socket.ValueKind == JsonValueKind.Null) continue;
                    var socketSlug = socket.GetProperty("slug").GetString() ?? "";
                    var socketType = socket.GetProperty("type").GetString() ?? "";
                    sockets.Add($"{socketSlug} ({socketType})");
                }
                if (sockets.Count > 0)
                    Console.WriteLine($"    Sockets: {string.Join(", ", sockets)}");
            }

            // Tempering stats
            if (modifiers.TryGetProperty("temperingStats", out var temperingStats) &&
                temperingStats.ValueKind == JsonValueKind.Array)
            {
                var tempers = new List<string>();
                foreach (var stat in temperingStats.EnumerateArray())
                {
                    if (stat.ValueKind == JsonValueKind.Null) continue;
                    var statId = stat.GetProperty("id").GetString() ?? "";
                    var isGreater = stat.TryGetProperty("isGreater", out var g) && g.ValueKind == JsonValueKind.True;
                    tempers.Add(isGreater ? $"{statId} [GA]" : statId);
                }
                if (tempers.Count > 0)
                    Console.WriteLine($"    Tempering: {string.Join(", ", tempers)}");
            }

            // Transfigured stats
            if (modifiers.TryGetProperty("transfiguredStats", out var transfiguredStats) &&
                transfiguredStats.ValueKind == JsonValueKind.Array)
            {
                var trans = new List<string>();
                foreach (var stat in transfiguredStats.EnumerateArray())
                {
                    if (stat.ValueKind == JsonValueKind.Null) continue;
                    if (stat.TryGetProperty("id", out var id))
                        trans.Add(id.GetString() ?? "");
                }
                if (trans.Count > 0)
                    Console.WriteLine($"    Transfigured: {string.Join(", ", trans)}");
            }

            // Kullean Transfigured stats
            if (modifiers.TryGetProperty("kulleanTransfiguredStats", out var kulleanStats) &&
                kulleanStats.ValueKind == JsonValueKind.Array)
            {
                var kullean = new List<string>();
                foreach (var stat in kulleanStats.EnumerateArray())
                {
                    if (stat.ValueKind == JsonValueKind.Null) continue;
                    if (stat.TryGetProperty("id", out var id))
                        kullean.Add(id.GetString() ?? "");
                }
                if (kullean.Count > 0)
                    Console.WriteLine($"    Kullean Transfigured: {string.Join(", ", kullean)}");
            }
        }

        Console.WriteLine();
    }
}

string JsonPrettify(string json)
{
    try
    {
        var doc = JsonDocument.Parse(json);
        return JsonSerializer.Serialize(doc, new JsonSerializerOptions { WriteIndented = true });
    }
    catch
    {
        return json;
    }
}
