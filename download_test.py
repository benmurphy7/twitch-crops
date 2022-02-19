import subprocess

if __name__ == '__main__':
    video_id = '1237401551';
    try:
        proc = subprocess.Popen(['node', 'download.js', video_id],
                                shell=False,
                                stdout=subprocess.PIPE
                                )
        while proc.poll() is None:
            stdout_line = proc.stdout.readline().decode('UTF-8')
            if stdout_line:
                print(stdout_line)
                #yield "data: %s\n\n" % stdout_line

    except Exception as e:
        print(e)