/* http://codeaid.net/javascript/convert-seconds-to-hours-minutes-and-seconds-%28javascript%29 */
function secondsToTime(secs){
    var hours = Math.floor(secs / (60 * 60));

    var divisor_for_minutes = secs % (60 * 60);
    var minutes = Math.floor(divisor_for_minutes / 60);
 
    var divisor_for_seconds = divisor_for_minutes % 60;
    var seconds = Math.ceil(divisor_for_seconds);
   
    var obj = {
        "h": hours,
        "m": minutes,
        "s": seconds
    };

    return obj;
}

/* allows to use '0'.repeat(...) */
String.prototype.repeat = function(num){
    if ( num == 0 ){
	return '';
    }
    return new Array( num + 1 ).join( this );
}

/* pads intergers with leading zeros */
function pad(x, width){
    s = x.toString();
    width -= s.length;
    return '0'.repeat(width) + s;
}

function format_time(x){
    var t = secondsToTime(x);
    return pad(t['h'], 2) + ':' + pad(t['m'], 2) + ':' + pad(t['s'],2);
}

function progressbar(pos, total, length){
    d = pos / total;
    n1 = Math.floor(d * length);
    n2 = length - n1;
    return '#'.repeat(n1) + '-'.repeat(n2);
}

$(document).everyTime(1000, function() {
    $.getJSON('/player/player_progress', function(data) {
	playing = data['playing'];
	
	if ( !playing ){
	    $('#status').html('<p>Not playing.</p>');
	    $('#progress').hide();
	    return;
	}

	pos = data['position'];
	length = data['length'];

	$('#status').html('<p>Currently playing: ' + data['filename'] + '</p>');
	$('#progress').show();
	$('#progress').html(
	    '<p>' + 
		format_time(pos) + 
		'&nbsp;' + 
		progressbar(pos, length, 25) + 
		'&nbsp;' + 
		format_time(length) +
	    '</p>');
    });
});

function seek(loc){
    action('seek/' + loc);
}

function stop(){
    action('stop');
}

function pause(){
    action('pause');
}

function loadfile(url){
    action('loadfile/' + url);
}

function action(x){
    $.ajax({
	url: '/player/' + x,
	complete: function(req, code) {
	    var data = req.responseText;
	    if ( req.status != 200 ){
		alert('Action "' + x + '" failed with code ' + req.status);
		return;
	    }

	    if ( data != '' ){
		alert('Action "' + x + '" failed: \n\n' + data);
		return;
	    }
	}
    });
}
