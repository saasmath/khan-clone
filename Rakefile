desc "Run hg purge & git clean, but exclude secrets and other dev env files"
task :clean do
    exclude_patterns = %w[
        secrets*.py
        .tags*
        deploy/node_modules
    ]
    args = exclude_patterns.map {|s| "-X \"#{s}\""}.join(" ")
    system "hg purge --all #{args}"
    Dir.chdir "khan-exercises" do
        system "git", "clean", "-xdf"
    end
end

desc "Compile handlebars templates"
task :handlebars do
    system "python", "deploy/compile_handlebar_templates.py"
end

desc "Compile jinja templates"
task :jinja do
    system "python", "deploy/compile_templates.py"
end

desc "Pack exercise files"
task :exercises do
    system "ruby", "khan-exercises/build/pack.rb"
end

desc "Compress javascript"
task :js do
    system "python", "deploy/compress.py", "js"
end

desc "Compress css"
task :css do
    system "python", "deploy/compress.py", "css"
end

desc "Commit build target in a form convenient for developers"
task :commit => [:lint, :unittest] do
end

desc "Commit build target"
task :build_commit => [:lint, :coverage] do
end

desc "Run lint checks"
task :lint do
    sh "tools/runpep8.sh"
end

desc "Run unit tests"
task :unittest do
    sh "tools/runtests.py"
end

desc "Run unit tests with XML test and code coverage reports"
task :coverage do
    omit = ["*_test.py",
            "*/google_appengine/*",
            "agar/*",
            "api/packages/*",
            "asynctools/*",
            "jinja2/*",
            "mapreduce/*",
            "tools/*",
            "webapp2.py",
            "webapp2_extras/*"
           ].join(",")
    sh "coverage run \"--omit=#{omit}\" tools/runtests.py --xml"
    sh "coverage xml"
    sh "coverage html"
end
