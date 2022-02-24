

function requestcomposer(id) {
    $.ajax({
        url: '/get_composer',
        data: {
            id: id
        },
        type: 'POST',
        success: function(res) {
            composer = JSON.parse(res)

            if (composer.previous == "break" && composer.next == "break") {
                $('#previous_button').hide();
                $('#next_button').hide();
            } else if (composer.previous == "break") {
                $('#previous_button').hide();
                $('#next_button').show();
            } else if (composer.next == "break") {
                $('#previous_button').show();
                $('#next_button').hide();
            } else {
                $('#previous_button').show();
                $('#next_button').show();
            }
            $('#previous_button').attr("onclick", 'requestcomposer(' + composer.previous + ')');
            $('#next_button').attr("onclick", 'requestcomposer(' + composer.next + ')');
            $('#fav_button').attr("onclick", 'favcomposer(' + composer.id + ')');

            if (composer.died == 2050) {
                composer.died = "present";
            }
            $('#composer-header').html('<b>' + composer.name_full + '</b>' + ' (' + composer.born + ' - ' + composer.died + ')');
            $('#composerbio').html(composer.introduction);
            $('#explore_button').attr("href", '/composer_router/' + composer.name_short);
            $('#explore_button').hide();
            $('#album_button').hide();
            $('#album_button').attr("href", '/composeralbums/' + composer.name_short +"/1");
            $('#loading_button').show();
            $('#composer-name').html('<b>' + composer.name_short + '</b> has been added to your favorites!');
            $('#wikilink').attr("href", composer.pageurl);
            $('.composerphoto').attr("src", 'https://storage.googleapis.com/composer-explorer.appspot.com/img/' + composer.name_short + '.jpg');
            $('.modalflag').attr("src", 'https://storage.googleapis.com/composer-explorer.appspot.com/' + composer.flagimg);
            $('#favorite-success').hide();
            $('#favorite-fail').hide();
            $('#composerModal').modal('show');
            playspotify(id);
            backgroundload(id);

        },
        error: function(error) {
            console.log(error);
        }
    });
}

function backgroundload(id){
    $.ajax({
        url: '/background_load',
        data: {
            id: id
        },
        type: 'POST',
        success: function(res) {
            if (res=="EXPLORE") {
                $('#explore_button').show();
            } else {
                $('#album_button').show();
            }
            $('#loading_button').hide();
            console.log(res);
        },
        error: function(error) {
            $('#loading_button').hide();
        }
    });
}

function getspotify() {
    $('#getspotifymodal').modal('show');
}

function playspotify(id) {
    $.ajax({
        url: '/play_spotify',
        data: {
            id: id
        },
        type: 'POST',
        success: function(res) {
            if(res != "Premium"){
                fadein(res);
            }
        },
        error: function(error) {
            console.log(error);
        }
    });
}

var beepTwo = $("#preview_audio");

function fadein(url){
        beepTwo.attr("src", url);
         beepTwo[0].volume = 0;
         beepTwo[0].play();
         beepTwo.animate({volume: 1}, 1500);
}

function fadeout(url){
    beepTwo.attr("src", url);
        beepTwo.animate({volume: 0}, 500, 'swing', function() {
            // really stop the music
            //beepTwo[0].pause();
        });
}

function preview_audio(url){
    beepTwo.attr("src", url);
    if (beepTwo[0].paused == false) {
        beepTwo.animate({volume: 0}, 500, 'swing', function() {
            // really stop the music
            beepTwo[0].pause();
        });
     } else {
         beepTwo[0].volume = 0;
         beepTwo[0].play();
         beepTwo.animate({volume: 1}, 1500);
     }
}


function pausespotify() {
    fadeout(beepTwo.src);
    $('#play-btn').show();
    $('#pause-btn').hide();
    $.ajax({
        url: '/pause_spotify',
        type: 'POST',
        success: function(res) {},
        error: function(error) {
            console.log(error);
        }
    });
}



function randomcomposer(list) {
    var length = list.length - 1
    var index = Math.floor(Math.random() * length);
    var id = list[index]
    requestcomposer(id)
}

function getUrlVars() {
    var vars = {};
    var parts = window.location.href.replace(/[?&]+([^=&]+)=([^&]*)/gi, function(m, key, value) {
        vars[key] = value;
    });
    return vars;
}

function favcomposer(id) {
    $.ajax({
        url: '/fav_composer',
        data: {
            id: id
        },
        type: 'POST',
        success: function(res) {
            $('#favorite-success').show();
            $('#favorite-success').html(res);
            console.log(res);
        },
        error: function(error) {
            $('#favorite-fail').show();
            console.log(error);
        }
    });
}

function requestwork(id) {
    $('.spinner').show();
    $.ajax({
        url: '/search_spotify',
        data: {
            id: id
        },
        type: 'POST',
        success: function(res) {
            console.log(res);
            window.location.href = "/albums/" + id;
        },
        error: function(error) {
            $('.spinner').hide();
            $('#' + id).popover('show');
        setTimeout(function(){
            $('#' + id).popover('hide');
        }, 2000);
        }
    });
}

function goBack() {
  window.history.back();
}

function requestsearchwork(id) {
    $('.spinner').show();
    $.ajax({
        url: '/search_spotify',
        data: {
            id: id
        },
        type: 'POST',
        success: function(res) {
            console.log(res);
            window.location.href = "/albums/" + id;
        },
        error: function(error) {
            $('.spinner').hide();
            alert("No Spotify tracks found for work.")
        }
    });
}

function showlikes(id) {
    $.ajax({
        url: '/get_album_likes',
        data: {
            id: id
        },
        type: 'POST',
        success: function(res) {
            users = JSON.parse(res)
            var i;
            var text = "";
            var newtext = "";
            for (i = 0; i < users.length; i++) {
                newtext = '<a href="/user/'+ users[i].username +'">' + users[i].display_name + '</a><br>';
                text = text + newtext;
            }
            $('#users-liked').html(
                text
            );

            $('#show-likes-modal').modal('show');
        },
        error: function(error) {
            console.log(error);
        }
    });
}



function createplaylist() {
    $.ajax({
        url: '/get_playlists',

        type: 'GET',
        success: function(res) {
            console.log(res);

            playlists = JSON.parse(res);

            var selected = [];
            $("input:checkbox[name=album]:checked").each(function(){
                selected.push($(this).val());
            });

            tracks = JSON.stringify(selected);

            $('#tracks').val(tracks)

            $('#existing-playlist').empty();
            $('#existing-playlist').append($('<option></option>').val("Choose").html("Choose"));
            $.each(playlists, function(i, p) {
                $('#existing-playlist').append($('<option></option>').val(p).html(p));
            });

            $('#createplaylistmodal').modal('show');
        },
        error: function(error) {
            $('#alert-message').html(error.responseText);
            $('#alert-modal').modal('show');
        }
    });
}

function deletetracks(work_id) {
    var selected = [];
    $("input:checkbox[name=album]:checked").each(function(){
        selected.push($(this).val());
    });
    tracks = JSON.stringify(selected);
    workid = work_id;

    $.ajax({
        url: '/delete_tracks',
        data: {
            tracks: tracks,
            workid: workid
        },
        type: 'POST',
        success: function(res) {
            alert(res);
        },
        error: function(error) {
            alert(error.responseText);
        }
    });
}

function createComposerPlaylist() {
    $('#composerplaylistmodal').modal('show');
}

function notLoggedIn(){
    $('#alert-modal').modal('show');
}

function wikiwork(search_item){
    var pageid = "";

    var url = "https://en.wikipedia.org/w/api.php";

    var params = {
        action: "query",
        list: "search",
        srsearch: search_item,
        srlimit: 1,
        format: "json"
    };

    url = url + "?origin=*";
    Object.keys(params).forEach(function(key){url += "&" + key + "=" + params[key];});

    fetch(url)
        .then(function(response){return response.json();})
        .then(function(response) {
            $('#wiki-title').text(response.query.search[0].title);
            pageid = response.query.search[0].pageid;
            // $('#wiki-text').html(response.query.search[0].snippet);
            // $('#wiki-info-modal').modal('show');
            var url2 = "https://en.wikipedia.org/w/api.php";

            var params2 = {
                action: "query",
                pageids: pageid,
                prop: "extracts&exintro&explaintext",
                redirects: 1,
                format: "json"
            };

            url2 = url2 + "?origin=*";
            Object.keys(params2).forEach(function(key){url2 += "&" + key + "=" + params2[key];});

            fetch(url2)
                .then(function(response){return response.json();})
                .then(function(response) {

                    for (var id in response.query.pages) {
                        $('#wiki-text').html(response.query.pages[id].extract);
                        pagetitle = response.query.pages[id].title;
                        wikiurl = "https://en.wikipedia.org/wiki/" + pagetitle;
                        $('#wikimorelink').attr("href", wikiurl);

                        break;
                    }
                    $('#wiki-info-modal').modal('show');
                })
                .catch(function(error){console.log(error);});
        })
        .catch(function(error){console.log(error);});
}
