'use strict';

angular.module("PyPushApp", ["ngResource"])
	.controller("PushList", function($scope, $resource, $timeout){
		var Microbot = $resource('/api/microbot/:id', {id: '@id'}, {
			query: {method: 'get', isArray: true},
		});

		var MicrobotAction = $resource("/api/microbot/:id/:action", {id: "@id", action: "@action"})
		
		$scope.microbots = [];

		$scope.doAction = (function(uuid, action)
		{
			MicrobotAction.get({id: uuid, action: action});
		});
		

		(function tick() {
	        $scope.microbots = Microbot.query(function(){
	            $timeout(tick, 5000);
	        });
	    })();
	});