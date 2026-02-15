require "sinatra/base"

class ApiApp < Sinatra::Base
  get "/public" do
    "ok"
  end

  post "/login" do
    authenticate!
    "created"
  end

  put "/users/:id" do
    "updated"
  end
end
