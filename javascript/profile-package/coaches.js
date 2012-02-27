var Coaches = {
    coachCollection: null,
    requestCollection: null,
    url: "/api/v1/user/coaches",

    init: function() {
        var email = Profile.profile.get("email"),
            template = Templates.get("profile.coaches");

        $("#tab-content-coaches").html(template({email: email}));

        this.delegateEvents_();

        return $.ajax({
            type: "GET",
            url: this.url,
            data: {
                email: email,
                casing: "camel"
            },
            dataType: "json",
            success: _.bind(this.onDataLoaded_, this)
        });
    },

    save: function() {
        var options = {
            url: this.url,
            contentType: "application/json"
        };

        var json = [];

        this.requestCollection.each(function(model) {
            json.push(model.toJSON());
        });

        this.coachCollection.each(function(model) {
            json.push(model.toJSON());
        });

        options["data"] = JSON.stringify(json);

        Backbone.sync("update", null, options);
    },

    onDataLoaded_: function(users) {
        var coaches = [],
            requests = [];

        _.each(users, function(user) {
            if (user.isCoachingLoggedInUser) {
                coaches.push(user);
            } else {
                requests.push(user);
            }
        });

        this.coachCollection = new Coaches.CoachCollection(coaches);

        new Coaches.CoachCollectionView({
            collection: Coaches.coachCollection,
            el: "#coach-list-container",
            emptyTemplateName: "profile.no-coaches"
        }).render();

        this.requestCollection = new Coaches.CoachCollection(requests);

        if(!this.requestCollection.isEmpty()) {
            $("#requests").show();

            new Coaches.CoachCollectionView({
                collection: Coaches.requestCollection,
                el: "#request-list-container",
                emptyTemplateName: "profile.no-requests"
            }).render();
        }
    },

    delegateEvents_: function() {
        $("#tab-content-coaches").on("keyup", "#coach-email",
            _.bind(this.onCoachEmailKeyup_, this));
        $("#tab-content-coaches").on("click", "#add-coach", this.onAddCoach_);
    },

    onCoachEmailKeyup_: function(e) {
        if (e.keyCode === $.ui.keyCode.ENTER) {
            this.onAddCoach_();
        }
    },

    onAddCoach_: function() {
        var email = $.trim($("#coach-email").val()),
            attrs = {
                email: email,
                isCoachingLoggedInUser: true
            };

        if (email) {
            this.coachCollection.add(attrs);
            this.save();
            $("#coach-email").val("");
        }
    }
};

Coaches.CoachView = Backbone.View.extend({
    className: "coach-row",

    // The corresponding Coach.CoachCollection
    collection_: null,
    template_: null,

    events: {
        "click .controls .remove": "onRemoveCoach_",
        "click .controls .accept": "onAcceptCoach_",
        "click .controls .deny": "onDenyCoach_"
    },

    initialize: function(options) {
        this.collection_ = options.collection;
        this.template_ = Templates.get("profile.coach");
    },

    render: function() {
        var context = this.model.toJSON();
        $(this.el).html(this.template_(context));

        // TODO(marcia): Figure out why I need to call this..
        this.delegateEvents();

        return this;
    },

    onRemoveCoach_: function() {
        this.collection_.remove(this.model);
        Coaches.save();
    },

    onAcceptCoach_: function() {
        this.collection_.remove(this.model);
        this.model.set({
            isCoachingLoggedInUser: true,
            isRequestingToCoachLoggedInUser: false
        });

        Coaches.coachCollection.add(this.model);
        Coaches.save();
    },

    onDenyCoach_: function() {
        this.collection_.remove(this.model);
        Coaches.save();
    }

});

Coaches.CoachCollection = Backbone.Collection.extend({
    model: Coaches.Coach
});

Coaches.CoachCollectionView = Backbone.View.extend({
    initialize: function(options) {
        this.coachViews_ = [];
        this.emptyTemplateName_ = options["emptyTemplateName"];

        this.collection.each(this.add, this);

        this.collection.bind("add", this.add, this);
        this.collection.bind("remove", this.remove, this);

    },

    add: function(model) {
        var coachView = new Coaches.CoachView({
            model: model,
            collection: this.collection
        });
        this.coachViews_.push(coachView);
        this.render();
    },

    remove: function(model) {
        var viewToRemove = _.find(this.coachViews_, function(view) {
                return view.model === model;
            });

        if (viewToRemove) {
            this.coachViews_ = _.without(this.coachViews_, viewToRemove);
            this.render();
        }
    },

    getEmptyNotification_: function() {
        if (!this.emptyNotification_) {
            var template = Templates.get(this.emptyTemplateName_);
            this.emptyNotification_ = template();
        }
        return this.emptyNotification_;
    },

    render: function() {
        $(this.el).empty();

        if (this.collection.isEmpty()) {
            $(this.el).append(this.getEmptyNotification_());
        } else {
            _.each(this.coachViews_, function(view) {
                $(this.el).prepend(view.render().el);
            }, this);
        }

        return this;
    }
});
