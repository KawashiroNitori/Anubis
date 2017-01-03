/**
 * Created by Nitori on 2016/12/30.
 */
'use strict';
import gulp from 'gulp';
import svgmin from 'gulp-svgmin';
import iconfont from 'gulp-iconfont';
import nunjucks from 'gulp-nunjucks';
import generateConstant from './scripts/build/constant/gulp';
import generateLocale from './scripts/build/constant/gulp';

const iconTimestamp = ~~(Date.now() / 1000);

gulp.task('constant', () => {
    return gulp
        .src('anubis/ui/constant/*.js')
        .pipe(generateConstant())
        .pipe(gulp.dest('anubis/constant'))
});
