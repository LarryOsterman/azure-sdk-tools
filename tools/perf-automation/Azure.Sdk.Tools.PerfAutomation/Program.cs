using Azure.Sdk.Tools.PerfAutomation.Models;
using CommandLine;
using CommandLine.Text;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using YamlDotNet.Core;
using YamlDotNet.Serialization;

namespace Azure.Sdk.Tools.PerfAutomation
{
    public static class Program
    {
        private static OptionsDefinition Options { get; set; }

        private static readonly JsonSerializerOptions JsonOptions = new JsonSerializerOptions
        {
            WriteIndented = true,
            Converters =
            {
                new JsonStringEnumConverter(JsonNamingPolicy.CamelCase)
            }
        };

        private class OptionsDefinition
        {
            [Option('d', "debug")]
            public bool Debug { get; set; }

            [Option('l', "languages")]
            public IEnumerable<Language> Languages { get; set; }

            [Option('i', "inputFile", Default = "input.yml")]
            public string InputFile { get; set; }

            [Option('o', "outputFile", Default = "output.json")]
            public string OutputFile { get; set; }

            [Option('t', "testFilter", HelpText = "Regex of tests to run")]
            public string TestFilter { get; set; }

            [Option("workingDirectoryNet")]
            public string WorkingDirectoryNet { get; set; }
        }

        public static async Task Main(string[] args)
        {
            var parser = new CommandLine.Parser(settings =>
            {
                settings.CaseSensitive = false;
                settings.CaseInsensitiveEnumValues = true;
                settings.HelpWriter = null;
            });

            var parserResult = parser.ParseArguments<OptionsDefinition>(args);

            await parserResult.MapResult(
                options => Run(options),
                errors => DisplayHelp(parserResult)
            );
        }

        static Task DisplayHelp<T>(ParserResult<T> result)
        {
            var helpText = HelpText.AutoBuild(result, settings =>
            {
                settings.AddEnumValuesToHelpText = true;
                return settings;
            });

            Console.Error.WriteLine(helpText);

            return Task.CompletedTask;
        }

        private static async Task Run(OptionsDefinition options)
        {
            Options = options;

            var uniqueOutputFile = GetUniquePath(options.OutputFile);

            var parser = new MergingParser(new YamlDotNet.Core.Parser(File.OpenText(options.InputFile)));

            var deserializer = new Deserializer();
            var tests = deserializer.Deserialize<List<Test>>(parser);

            List<Result> results = new List<Result>();

            var selectedTests = tests.Where(t =>
                String.IsNullOrEmpty(options.TestFilter) || Regex.IsMatch(t.Name, options.TestFilter, RegexOptions.IgnoreCase));

            foreach (var test in selectedTests)
            {
                var selectedLanguages = test.Languages.Where(l => !options.Languages.Any() || options.Languages.Contains(l.Key));

                foreach (var language in selectedLanguages)
                {
                    foreach (var arguments in test.Arguments)
                    {
                        DebugWriteLine($"Test: {test.Name}, Language: {language.Key}, " +
                            $"TestName: {language.Value.TestName}, Arguments: {arguments}");
                        foreach (var packageVersions in language.Value.PackageVersions)
                        {
                            DebugWriteLine("===");
                            foreach (var packageVersion in packageVersions)
                            {
                                DebugWriteLine($"  Name: {packageVersion.Key}, Version: {packageVersion.Value}");
                            }

                            Result result = null;

                            switch (language.Key)
                            {
                                case Language.Net:
                                    result = await Net.RunAsync(options.WorkingDirectoryNet, options.Debug, language.Value, arguments, packageVersions);
                                    break;
                                default:
                                    continue;
                            }

                            if (result != null)
                            {
                                result.TestName = test.Name;

                                result.Language = language.Key;
                                result.Project = language.Value.Project;
                                result.LanguageTestName = language.Value.TestName;
                                result.Arguments = arguments;
                                result.PackageVersions = packageVersions;
                            }

                            results.Add(result);

                            using var stream = File.OpenWrite(uniqueOutputFile);
                            await JsonSerializer.SerializeAsync(stream, results, JsonOptions);
                        }
                    }

                }
            }
        }

        private static string GetUniquePath(string path)
        {
            var directoryName = Path.GetDirectoryName(path);
            var fileNameWithoutExtension = Path.GetFileNameWithoutExtension(path);
            var extension = Path.GetExtension(path);

            var uniquePath = Path.Join(directoryName, $"{fileNameWithoutExtension}{extension}");

            int index = 0;
            while (File.Exists(uniquePath))
            {
                index++;
                uniquePath = Path.Join(directoryName, $"{fileNameWithoutExtension}.{index}{extension}");
            }

            using var stream = File.Create(uniquePath);

            return uniquePath;
        }

        private static void DebugWriteLine(string value)
        {
            if (Options.Debug)
            {
                Console.WriteLine(value);
            }
        }
    }
}
