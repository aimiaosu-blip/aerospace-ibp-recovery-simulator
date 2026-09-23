// 1. Create a Text parameter named CsvFolder containing the absolute artifacts/csv path.
// 2. Create a blank query named LoadAeroPlanCsv, paste this function in Advanced Editor.
// 3. Create reference queries, e.g. = LoadAeroPlanCsv("production_plan")
// 4. Apply the explicit types in dashboard_spec.md; do not rely on locale inference.
(FileBaseName as text) as table =>
let
    Folder = Text.TrimEnd(CsvFolder, {"/", "\"}),
    Source = Csv.Document(File.Contents(Folder & "/" & FileBaseName & ".csv"),
        [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true])
in
    Headers
