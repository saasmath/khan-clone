var Coaches = {
    coachCollection: null,
    requestCollection: null,
    url: "/api/v1/user/coaches",

    init: function() {
        var isSelf = Profile.profile.get("isSelf"),
            isPhantom = Profile.profile.get("isPhantom"),
            deferred;

        if (isSelf && !isPhantom) {
            var email = Profile.profile.get("email"),
                template = Templates.get("profile.coaches");
            $("#tab-content-coaches").html(template(Profile.profile.toJSON()));

            this.delegateEvents_();

            deferred = $.ajax({
                type: "GET",
                url: this.url,
                data: {
                    email: email,
                    casing: "camel"
                },
                dataType: "json",
                success: _.bind(this.onDataLoaded_, this)
            });
        } else {
            deferred = new $.Deferred().resolve();
        }

        return deferred;
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

    // TODO(marcia): Throttle to avoid inconsistent state
    save: function() {
        var options = {
            url: this.url,
            contentType: "application/json",
            success: _.bind(this.onSaveSuccess_, this),
            error: _.bind(this.onSaveError_, this)
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

    onSaveSuccess_: function() {
        $("#coach-email").val("");
        this.coachCollection.markCoachesAsSaved();
    },

    onSaveError_: function() {
        this.coachCollection.removeUnsavedCoaches();
        this.showError_("We couldn't find anyone with that email.")
    },

    delegateEvents_: function() {
        $("#tab-content-coaches").on("keyup", "#coach-email",
            _.bind(this.onCoachEmailKeyup_, this));
        $("#tab-content-coaches").on("click", "#add-coach",
            _.bind(this.onAddCoach_, this));
    },

    // TODO(marcia): Check out the utility in benkomalo2
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
            var model = null;
            if (this.coachCollection.findByEmail(email)) {
                var message = email + " is already your coach.";
                this.showError_(message);
            } else if (model = this.requestCollection.findByEmail(email)){
                this.acceptCoachRequest(model);
            } else {
                this.coachCollection.add(attrs);
                this.save();
            }
        }
    },

    showError_: function(message) {
        $(".coaches-section .notification.error").text(message)
            .show()
            .delay(2000)
            .fadeOut(function() {
                $(this).text("");
            });
    },

    acceptCoachRequest: function(model) {
        this.requestCollection.remove(model);
        model.set({
            isCoachingLoggedInUser: true,
            isRequestingToCoachLoggedInUser: false
        });

        Coaches.coachCollection.add(model);
        Coaches.save();
    }
};

Coaches.CoachView = Backbone.View.extend({
    className: "coach-row",

    // The corresponding Coaches.CoachCollection
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
        Coaches.acceptCoachRequest(this.model);
    },

    onDenyCoach_: function() {
        this.collection_.remove(this.model);
        Coaches.save();
    }

});

Coaches.Coach = ProfileModel.extend({
    /**
     * Override toJSON to delete the id attribute since it is only used for
     * client-side bookkeeping.
     */
    toJSON: function() {
        var json = Coaches.Coach.__super__.toJSON.call(this);
        delete json["id"];
        return json;
    }
})

Coaches.CoachCollection = Backbone.Collection.extend({
    model: Coaches.Coach,

    initialize: function() {
        this.markCoachesAsSaved();
    },

    findByEmail: function(email) {
        return this.find(function(model) {
            return model.get("email") === email;
        });
    },

    /**
     * Mark which coach models have been saved to server,
     * which lets us remove un-saved / invalid coaches on error.
     */
    markCoachesAsSaved: function() {
        this.each(function(model) {
            // Backbone models without an id are considered
            // to be new, as in not yet saved to server.
            model.set({id: "marks-model-as-saved-on-server"});
        });
    },

    removeUnsavedCoaches: function() {
        var modelsToRemove = this.filter(function(model) {
            return model.isNew();
        });

        this.remove(modelsToRemove);
    }
});

Coaches.CoachCollectionView = Backbone.View.extend({
    rendered_: false,

    initialize: function(options) {
        this.coachViews_ = [];
        this.emptyTemplateName_ = options["emptyTemplateName"];

        this.collection.each(this.add, this);

        this.collection.bind("add", this.add, this);
        this.collection.bind("remove", this.remove, this);
        this.collection.bind("add", this.handleEmptyNotification_, this);
        this.collection.bind("remove", this.handleEmptyNotification_, this);
    },

    add: function(model) {
        var coachView = new Coaches.CoachView({
            model: model,
            collection: this.collection
        });
        this.coachViews_.push(coachView);
        if (this.rendered_) {
            $(this.el).prepend(coachView.render().el);
        }
    },

    remove: function(model) {
        var viewToRemove = _.find(this.coachViews_, function(view) {
                return view.model === model;
            });

        if (viewToRemove) {
            this.coachViews_ = _.without(this.coachViews_, viewToRemove);
            if (this.rendered_){
                $(viewToRemove.el).fadeOut(function() {
                    viewToRemove.remove();
                });
            }
        }
    },

    showEmptyNotification_: function() {
        if (!this.emptyNotification_) {
            var template = Templates.get(this.emptyTemplateName_);
            this.emptyNotification_ = $("<div>").addClass("empty-notification").html(template());
            $(this.el).append(this.emptyNotification_);
        }
        this.$(".empty-notification").show();
    },

    handleEmptyNotification_: function() {
        if (this.collection.isEmpty()) {
            this.showEmptyNotification_();
        } else {
            this.$(".empty-notification").hide();
        }
    },

    render: function() {
        this.rendered_ = true;
        $(this.el).empty();

        this.handleEmptyNotification_();

        _.each(this.coachViews_, function(view) {
            $(this.el).prepend(view.render().el);
        }, this);

        return this;
    }
});
