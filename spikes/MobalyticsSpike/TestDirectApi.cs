// This file tests whether we can call the GraphQL API directly
// without needing a browser at all
using System.Text;
using System.Text.Json;

public static class DirectApiTest
{
    public static async Task RunAsync()
    {
        Console.WriteLine("\n=== Testing Direct GraphQL API Call ===\n");

        var handler = new HttpClientHandler();
        using var client = new HttpClient(handler);

        // Set headers to mimic a real browser
        client.DefaultRequestHeaders.Add("User-Agent",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36");
        client.DefaultRequestHeaders.Add("Accept", "application/json");
        client.DefaultRequestHeaders.Add("Accept-Language", "en-US,en;q=0.9");
        client.DefaultRequestHeaders.Add("Origin", "https://mobalytics.gg");
        client.DefaultRequestHeaders.Add("Referer", "https://mobalytics.gg/diablo-4/builds/barbarian-whirl-wind-barb");

        // Minimal query that requests just the build variant equipment data
        var query = @"query Diablo4UgFeaturedDocumentQuery($input: Diablo4UserGeneratedDocumentInputBySlug!) {
  game: diablo4 {
    documents {
      userGeneratedDocumentBySlug(input: $input) {
        error
        data {
          id
          slugifiedName
          type
          data {
            name
            buildVariants {
              values {
                id
                genericBuilder {
                  slots {
                    gameSlotSlug
                    gameEntity {
                      slug
                      title
                      type
                      iconUrl
                      color
                      modifiers {
                        gearStats {
                          id
                          isGreater
                          isMasterwork
                        }
                        implicitStats {
                          id
                        }
                        socketStats {
                          slug
                          type
                        }
                        temperingStats {
                          id
                          isGreater
                          isMasterwork
                        }
                        sealStats {
                          id
                        }
                        charmStats {
                          id
                        }
                        transfiguredStats {
                          id
                        }
                      }
                      entity {
                        ... on D4Aspect {
                          __typename
                          iconUrl
                          title: name
                        }
                        ... on D4UniqueItem {
                          __typename
                          iconUrl
                          title: name
                          chaos
                          mythic
                        }
                      }
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}";

        var payload = new
        {
            query,
            variables = new
            {
                input = new
                {
                    slug = "barbarian-whirl-wind-barb",
                    type = "builds",
                    widgetsOverride = Array.Empty<object>()
                }
            },
            operationName = "Diablo4UgFeaturedDocumentQuery"
        };

        var json = JsonSerializer.Serialize(payload);
        var content = new StringContent(json, Encoding.UTF8, "application/json");

        try
        {
            Console.WriteLine("Sending direct GraphQL request...");
            var response = await client.PostAsync("https://mobalytics.gg/api/diablo4/v4/graphql/query", content);

            Console.WriteLine($"Status: {response.StatusCode}");
            Console.WriteLine($"Headers:");
            foreach (var header in response.Headers)
            {
                Console.WriteLine($"  {header.Key}: {string.Join(", ", header.Value)}");
            }

            var responseBody = await response.Content.ReadAsStringAsync();
            Console.WriteLine($"Response length: {responseBody.Length}");

            if (response.IsSuccessStatusCode)
            {
                Console.WriteLine("\n*** DIRECT API CALL WORKS! ***\n");
                // Pretty print first 2000 chars
                try
                {
                    var doc = JsonDocument.Parse(responseBody);
                    var pretty = JsonSerializer.Serialize(doc, new JsonSerializerOptions { WriteIndented = true });
                    Console.WriteLine(pretty.Length > 3000 ? pretty[..3000] + "\n..." : pretty);

                    // Save full response
                    await File.WriteAllTextAsync(
                        @"D:\git\home\spikes\MobalyticsSpike\direct-api-response.json",
                        pretty);
                    Console.WriteLine("\nFull response saved to direct-api-response.json");
                }
                catch
                {
                    Console.WriteLine(responseBody.Length > 2000 ? responseBody[..2000] : responseBody);
                }
            }
            else
            {
                Console.WriteLine($"\nDirect API call BLOCKED (status {response.StatusCode})");
                Console.WriteLine(responseBody.Length > 500 ? responseBody[..500] : responseBody);
            }
        }
        catch (Exception ex)
        {
            Console.WriteLine($"Direct API call FAILED: {ex.GetType().Name}: {ex.Message}");
            if (ex.InnerException != null)
                Console.WriteLine($"  Inner: {ex.InnerException.GetType().Name}: {ex.InnerException.Message}");
        }
    }
}
