const fs = require('fs');
const XMLHttpRequest = require('xhr2');

const video_id = '1249134654';
const clientInfo = fs.readFileSync('clientInfo.txt', 'utf8').split('\n');
var token;

items = [];

commentMap = {}
chunkMap = {}

cursorMap = {}
cursorQueue = []

const progressUpdate = setInterval(showProgress, 500)

var total_comments = 0;

var total_duration;
var logged_duration;

mainFlow();

async function mainFlow() {
    token = await getAccessToken()
    multiThreadDownload(video_id, 200)
}


async function multiThreadDownload(video_id, threads) {
    if (fs.existsSync(video_id)) {
        fs.rmSync(video_id, { recursive: true, force: true });
    }

    if (!fs.existsSync(video_id)){
        fs.mkdirSync(video_id);
    }

    const seconds = await getSeconds(video_id);
    total_duration = seconds;
    logged_duration = 0;
    showProgress();
    const section_dist = seconds / threads

    var promiseArray = [];

    for (let i=threads; i > 0; i--) {
        offset = section_dist * (i-1);
        //console.log(`Thread ${i} = offset: ${offset}`);
        promiseArray.push(logChunk(i, video_id, offset, null));
    }

    await Promise.all(promiseArray);
    logged_duration = total_duration;
    clearInterval(progressUpdate);
    showProgress();
    console.log("Download Complete!")
    console.log(`total comments: ${total_comments}`)
    //console.log(cursorQueue);

    // Stitch together section files

    items = Object.keys(chunkMap).map(function(key) {
        return [key, chunkMap[key]];
    });
    items.sort(function(first, second) {
        return first[1] - second[1];
    });

    //console.log(items);

    await stitchLogs(video_id);
    console.log("DONE!");
    
}

function writeFile(file, content) {
    if (content == '') {
        return;
    }

    fs.writeFileSync(file, content);
}

function appendFile(dest_file, source_file) {
    const data = fs.readFileSync(source_file, {encoding:'utf8', flag:'r'});

    fs.appendFileSync(dest_file, data);

    /*
    fs.readFile(source_file, function (err, data) {
        if (err) throw err;

        fs.appendFile(dest_file, data, function (err) {
            if (err) throw err;
        });
    });
    */
}

async function stitchLogs(video_id) {
    const dest_file = `${video_id}.txt`;
    //var w = fs.createWriteStream(`${video_id}.txt`, {flags: 'a'});

    for (item of items) {
        const source_file = `${video_id}/${item[0]}`;

        appendFile(dest_file, source_file);

        //var r = fs.createReadStream(`${video_id}/${item[0]}`);
        //r.pipe(w);

    }

    return;
}

async function logChunk(thread, video_id, offset, cursor) {
    try {
        response = null;
        if (offset != null) {
            response = await getOffsetComments(video_id, offset)
        } 
        else if (cursor != null) {
            if (!cursorMap.hasOwnProperty(cursor)) {
                cursorMap[next_cursor] = thread;
                response = await getCursorComments(video_id, cursor)
            } else {
                console.log('repeat cursor');
                return;
            }
            //console.log(response)
        }
        if (response == null) {
            //console.log(`${thread}: REACHED END OF COMMENTS`);
            return 0;
        }
        comments = null;
        try {
            comments = response['comments'];
        } catch {
            console.log(response);
        }
    
        if (comments != null) {
            stop = true;
            chunk_id = comments[0]['_id'];
            comment_offset = comments[0]['content_offset_seconds'];

            if (!commentMap.hasOwnProperty(chunk_id)) {
                if (!chunkMap.hasOwnProperty(chunk_id)) {
                    chunkMap[chunk_id] = parseFloat(comment_offset);
                    stop = false;
                }
            }

            if (stop) {
                return;
            }

            content = '';
            for (comment of comments) {
                comment_id = comment['_id'];
                if (commentMap.hasOwnProperty(comment_id)) {
                    //console.log(`${thread}: REACHED END OF SECTION`);
                    //console.log(`Hit comment logged by: ${commentMap[comment['_id']]}`)
                    stop = true;
                    break;
                } else {
                    commentMap[comment_id] = parseFloat(comment_offset);
                }

                last_comment_offset = comment['content_offset_seconds'];
                seconds = parseInt(last_comment_offset);
                comment_line = `[${toTimestamp(seconds)}] <${comment['commenter']['display_name']}> ${comment['message']['body']}`;
                content += comment_line + "\n";
                total_comments += 1;
                //console.log(comment_line);
            }

            next_cursor = response['_next'];

            if (next_cursor) {
                content += next_cursor + " " + comment_offset + "\n";
            }
            
            try {
            writeFile(`${video_id}/${chunk_id}`, content);
            } catch (err) {
                console.log('write error');
                console.log(err);
            }

            logged_duration += (parseFloat(last_comment_offset) - parseFloat(comment_offset));

            if (stop) {
                return;
            }

            
            //next_cursor = cursorQueue.shift();
            
            if (next_cursor) {
                await logChunk(thread, video_id, null, next_cursor);
            } else {
                //console.log(next_cursor);
            }

            /*
            if (next_cursor) {
                //console.log(`Thread ${thread} taking cursor ${next_cursor}`)
                await logChunk(thread, video_id, null, next_cursor);
            }
            */
            
            //cursor = response['_next'];
            //await logChunk(thread, video_id, null, cursor);
        //console.log(`Thread ${thread} is returning`)
        } 
    } catch (error) {
        console.log(error);
    }
}


async function showProgress()
{
    process.stdout.write(`Downloading: ${(logged_duration/total_duration) * 100}%` + "\r");
}




async function getAccessToken() {
    var url = new URL(`https://id.twitch.tv/oauth2/token`);
    url.searchParams.append('client_id', clientInfo[0]);
    url.searchParams.append('client_secret', clientInfo[1]);
    url.searchParams.append('grant_type', 'client_credentials');

    let xhr = new XMLHttpRequest();
    xhr.open("POST", url.toString());
    response = await makeRequest(xhr);

    return JSON.parse(response);
}

async function getSeconds(video_id) {
    var url = new URL(`https://api.twitch.tv/helix/videos`);
    url.searchParams.append('id', video_id);

    let xhr = new XMLHttpRequest();
    
    xhr.open("GET", url.toString());
    xhr.setRequestHeader('Client-ID', clientInfo[0]);
    xhr.setRequestHeader('Authorization', 'Bearer ' + token['access_token']);

    response = await makeRequest(xhr);
    var obj = JSON.parse(response);
    var duration = obj['data'][0]['duration'];
   
    return toSeconds(duration);
}

async function getOffsetComments(video_id, offset) {
    var url = new URL(`https://api.twitch.tv/v5/videos/${video_id}/comments`);
    url.searchParams.append('content_offset_seconds', offset);
    
    let xhr = new XMLHttpRequest();
    
    xhr.open("GET", url.toString());
    xhr.setRequestHeader('Client-ID', clientInfo[0]);
    xhr.setRequestHeader('Authorization', clientInfo[1]);
    //xhr.setRequestHeader('Cache-Control', 'no-cache');
    
    return JSON.parse(await makeRequest(xhr));
}

async function getCursorComments(video_id, cursor) {
    var url = new URL(`https://api.twitch.tv/v5/videos/${video_id}/comments`);
    url.searchParams.append('cursor', cursor);
    
    let xhr = new XMLHttpRequest();
    
    xhr.open("GET", url.toString());
    xhr.setRequestHeader('Client-ID', clientInfo[0]);
    xhr.setRequestHeader('Authorization', clientInfo[1]);
    //xhr.setRequestHeader('Cache-Control', 'no-cache');
    
    return JSON.parse(await makeRequest(xhr));
}


function makeRequest(xhr) {
    return new Promise(function (resolve, reject) {
        xhr.onload = function () {
            if (this.status == 200) { //this.status >= 200 && this.status < 300
                //console.log(this.status);
                resolve(xhr.response);
            } else {
                resolve(xhr.response);
                console.log('FAIL RESPONSE')
                console.log(response);
                reject({
                    status: this.status,
                    statusText: xhr.statusText
                });
            }
        };
        xhr.onerror = function () {
            reject({
                status: this.status,
                statusText: xhr.statusText
            });
        };
        xhr.send();
    });
  }


  function toSeconds(duration) {
    if (duration.indexOf('h') == -1) {
        duration = '0h' + duration;
    }
    duration = duration.replace('h', ':').replace('m', ':').replace('s', '');
    parts = duration.split(':');

    return 3600 * parseInt(parts[0]) + 60 * parseInt(parts[1]) + parseInt(parts[2]);;
  }

// TODO: Handle times above 24 hours
function toTimestamp(seconds) {
    return new Date(1000 * seconds).toISOString().substr(11, 8)
}


/*
https://api.twitch.tv/v5/videos/{video_id}/comments

let xhr = new XMLHttpRequest();




function makeRequest(method, url) {
    return new Promise(function (resolve, reject) {
        let xhr = new XMLHttpRequest();
        xhr.open(method, url);
        xhr.setRequestHeader('Cache-Control', 'no-cache');
        xhr.onload = function () {
            if (this.status >= 200 && this.status < 300) {
                resolve(xhr.response);
            } else {
                reject({
                    status: this.status,
                    statusText: xhr.statusText
                });
            }
        };
        xhr.onerror = function () {
            reject({
                status: this.status,
                statusText: xhr.statusText
            });
        };
        xhr.send();
    });
  }
  */