using System.Text;
using System.Text.Json;

namespace D4LootFilter.Scraper;

public class MobalyticsClient
{
    private const string Endpoint = "https://mobalytics.gg/api/diablo4/v4/graphql/query";

    private const string Query = """
        query Diablo4UgFeaturedDocumentQuery($input: Diablo4UserGeneratedDocumentInputBySlug!) {
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
                              modifiers {
                                gearStats { id isGreater isMasterwork }
                                temperingStats { id isGreater isMasterwork }
                              }
                              entity {
                                ... on D4Aspect { __typename title: name }
                                ... on D4UniqueItem { __typename title: name chaos mythic }
                              }
                            }
                          }
                        }
                      }
                    }
                  }
                  content
                }
              }
            }
          }
        }
        """;

    private readonly HttpClient _httpClient;

    public MobalyticsClient(HttpClient httpClient)
    {
        _httpClient = httpClient;
    }

    public async Task<string> FetchBuildAsync(string slug, CancellationToken ct = default)
    {
        var payload = new
        {
            query = Query,
            variables = new
            {
                input = new
                {
                    slug,
                    type = "builds",
                    widgetsOverride = Array.Empty<object>(),
                }
            },
            operationName = "Diablo4UgFeaturedDocumentQuery",
        };

        var json = JsonSerializer.Serialize(payload);
        using var request = new HttpRequestMessage(HttpMethod.Post, Endpoint)
        {
            Content = new StringContent(json, Encoding.UTF8, "application/json"),
        };
        request.Headers.Add("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36");
        request.Headers.Add("Accept", "application/json");
        request.Headers.Add("Origin", "https://mobalytics.gg");
        request.Headers.Add("Referer", $"https://mobalytics.gg/diablo-4/builds/{slug}");

        using var response = await _httpClient.SendAsync(request, ct);
        response.EnsureSuccessStatusCode();
        return await response.Content.ReadAsStringAsync(ct);
    }
}
